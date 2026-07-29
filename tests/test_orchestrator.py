"""Tests for JobHunter agent orchestration."""

from pathlib import Path
from unittest.mock import MagicMock

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
from job_hunter.models.job_search_profile import JobSearchProfile


def _config(tmp_path: Path) -> AppConfig:
    prefs_file = tmp_path / "my_job_preferences.yaml"
    prefs_file.write_text("preferred_roles: []\nacceptable_roles: []\nexcluded_roles: []\n", encoding="utf-8")
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


def test_agent_run_processes_posting(tmp_path: Path) -> None:
    """Agent downloads, extracts, ranks, saves, and updates history."""
    config = _config(tmp_path)
    (tmp_path / "resume.md").write_text("# Resume", encoding="utf-8")
    profile = JobSearchProfile(target_titles=["Manager"])
    posting = JobPosting(
        title="Engineering Manager",
        company="Example Corp",
        location="Montreal",
        url="https://example.com/job/1",
        description="Lead teams",
    )
    posting.confidence_score = 0.95

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

    history.save.assert_called_once()
    history.add_entry.assert_called_once()
    resume.invoke.assert_called_once()


def test_agent_skips_duplicate(tmp_path: Path) -> None:
    """Duplicate postings update history and skip further processing."""
    config = _config(tmp_path)
    (tmp_path / "resume.md").write_text("# Resume", encoding="utf-8")
    profile = JobSearchProfile(target_titles=["Manager"])
    posting = JobPosting(title="Manager", company="Corp", location="Montreal", url="https://example.com/1")

    profile_service = MagicMock()
    profile_service.load_or_generate.return_value = profile
    history = MagicMock()
    history.is_duplicate.return_value = True
    search = MagicMock()
    search.discover_urls.return_value = ["https://example.com/1"]
    download = MagicMock()
    extract = MagicMock()
    extract.extract.return_value = posting
    rank = MagicMock()
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

    history.touch_duplicate.assert_called_once()
    rank.rank.assert_not_called()
    resume.invoke.assert_not_called()
