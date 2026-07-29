"""Tests for user job search preferences loading and workflow integration."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from job_hunter.agent.orchestrator import JobHunterAgent
from job_hunter.models.config import (
    AppConfig,
    JobSearchPreferencesConfig,
    ModelConfig,
    ResumeReworkConfig,
    SearchConfig,
    SearchProfileConfig,
    WebSitesConfig,
)
from job_hunter.models.job_posting import JobPosting
from job_hunter.models.job_search_preferences import JobSearchPreferences, PreferredRole, RolePreference
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.services.filtering_service import is_excluded_posting
from job_hunter.services.preferences_service import (
    build_search_titles,
    format_preferences_for_prompt,
    load_job_search_preferences,
)
from job_hunter.services.configuration_service import load_config
from job_hunter.tools.search.search_tool import SearchTool
from job_hunter.tools.search.company_provider import CompanyWebsiteSearchProvider
from job_hunter.tools.search.job_board_provider import JobBoardSearchProvider


def test_load_valid_preferences_file() -> None:
    """Valid preferences YAML loads preferred, acceptable, and excluded roles."""
    preferences = load_job_search_preferences(Path("tests/test_data/sample_job_preferences.yaml"))

    assert len(preferences.preferred_roles) == 2
    assert preferences.preferred_roles[0].title == "Software Development Manager"
    assert preferences.preferred_roles[0].priority == 1
    assert preferences.acceptable_roles[0].title == "Software Team Lead"
    assert preferences.excluded_roles[0].title == "Senior Software Developer"


def test_load_missing_preferences_file(tmp_path: Path) -> None:
    """Missing preferences file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_job_search_preferences(tmp_path / "missing.yaml")


def test_load_invalid_preferences_file(tmp_path: Path) -> None:
    """Invalid preferences schema raises ValueError."""
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("preferred_roles: not-a-list\n", encoding="utf-8")

    with pytest.raises(ValueError, match="preferred_roles must be a list"):
        load_job_search_preferences(invalid)


def test_build_search_titles_prefers_user_roles() -> None:
    """User preference titles appear before AI profile titles in search queries."""
    preferences = JobSearchPreferences(
        preferred_roles=[PreferredRole(title="QA Manager", priority=1)],
        acceptable_roles=[RolePreference(title="Team Lead")],
    )
    profile_titles = ["Engineering Manager", "QA Manager"]

    titles = build_search_titles(profile_titles, preferences)

    assert titles == ["QA Manager", "Team Lead", "Engineering Manager"]


def test_excluded_role_from_preferences_is_filtered() -> None:
    """User excluded roles are rejected before ranking."""
    posting = JobPosting(title="Senior Software Developer", company="Corp", location="Montreal", url="https://x")
    preferences = JobSearchPreferences(excluded_roles=[RolePreference(title="Senior Software Developer")])

    assert is_excluded_posting(posting, JobSearchProfile(), preferences)


def test_format_preferences_for_prompt_includes_sections() -> None:
    """Preferences are serialized for ranking prompts."""
    preferences = JobSearchPreferences(
        preferred_roles=[PreferredRole(title="Manager", priority=1, description="Lead teams")],
        excluded_roles=[RolePreference(title="Intern")],
    )

    text = format_preferences_for_prompt(preferences)

    assert "Preferred roles" in text
    assert "Manager" in text
    assert "Excluded roles" in text


def test_load_config_requires_preferences_file(tmp_path: Path) -> None:
    """Configuration loading validates that the preferences file exists."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
posting_output: "out"
posting_history: "history.yaml"
search_profile:
  input_files: ["resume.md"]
  output_file: "profile.yaml"
  job_search_preferences:
    file: "missing_preferences.yaml"
resume_rework:
  script_path: "script.py"
  working_directory: "."
""",
        encoding="utf-8",
    )
    (tmp_path / "resume.md").write_text("resume", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Job search preferences file not found"):
        load_config(config_file)


def _agent_config(tmp_path: Path) -> AppConfig:
    prefs_file = tmp_path / "my_job_preferences.yaml"
    prefs_file.write_text(
        "preferred_roles: []\nacceptable_roles: []\nexcluded_roles: []\n",
        encoding="utf-8",
    )
    return AppConfig(
        posting_output=tmp_path / "output",
        posting_history=tmp_path / "history.yaml",
        search_profile=SearchProfileConfig(
            input_files=[tmp_path / "resume.md"],
            output_file=tmp_path / "profile.yaml",
            job_search_preferences=JobSearchPreferencesConfig(file=prefs_file),
        ),
        resume_rework=ResumeReworkConfig(script_path=tmp_path / "resume_rework.py", working_directory=tmp_path),
        confidence_resume=0.9,
        models=ModelConfig("a", "b", "c", "d", "e"),
        locations=[],
        web_sites=WebSitesConfig(),
        search=SearchConfig(provider="serper"),
        config_path=tmp_path / "config.yaml",
    )


def test_agent_run_passes_preferences_to_search_and_ranking(tmp_path: Path) -> None:
    """Workflow loads preferences and passes them to search and ranking tools."""
    config = _agent_config(tmp_path)
    (tmp_path / "resume.md").write_text("# Resume", encoding="utf-8")
    profile = JobSearchProfile(target_titles=["Manager"])
    posting = JobPosting(
        title="Engineering Manager",
        company="Example Corp",
        location="Montreal",
        url="https://example.com/job/1",
        description="Lead teams",
    )

    profile_service = MagicMock()
    profile_service.load_or_generate.return_value = profile
    history = MagicMock()
    history.is_duplicate.return_value = False
    search = MagicMock()
    search.discover_urls.return_value = ["https://example.com/job/1"]
    download = MagicMock()
    download.download.return_value = "<html>job</html>"
    extract = MagicMock()
    extract.extract.return_value = posting
    rank = MagicMock()
    rank.should_process.return_value = (True, "")
    rank.rank.return_value = 0.95
    resume = MagicMock()

    agent = JobHunterAgent(
        config,
        profile_service=profile_service,
        history_service=history,
        search_tool=search,
        download_tool=download,
        extraction_tool=extract,
        ranking_tool=rank,
        resume_tool=resume,
    )

    agent.run(test_mode=True)

    search.discover_urls.assert_called_once()
    assert isinstance(search.discover_urls.call_args.args[1], JobSearchPreferences)
    rank.should_process.assert_called_once()
    assert isinstance(rank.should_process.call_args.args[2], JobSearchPreferences)
    rank.rank.assert_called_once()
    assert isinstance(rank.rank.call_args.args[3], JobSearchPreferences)


def test_search_tool_uses_preference_titles() -> None:
    """Search tool builds queries from combined profile and preference titles."""
    config = MagicMock()
    config.locations = []
    serper = MagicMock()
    serper.discover.return_value = []
    company = MagicMock(spec=CompanyWebsiteSearchProvider)
    company.discover_for_profile.return_value = []
    board = MagicMock(spec=JobBoardSearchProvider)
    board.discover_for_profile.return_value = []

    tool = SearchTool(config, serper, company, board)
    profile = JobSearchProfile(target_titles=["Engineering Manager"])
    preferences = JobSearchPreferences(preferred_roles=[PreferredRole(title="QA Manager", priority=1)])

    tool.discover_urls(profile, preferences)

    queries = serper.discover.call_args.args[0]
    assert any("QA Manager" in query for query in queries)
