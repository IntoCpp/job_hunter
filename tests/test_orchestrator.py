"""Tests for JobHunter agent orchestration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from job_hunter.agent.orchestrator import JobHunterAgent, RunOptions
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
from job_hunter.models.pipeline import RankingResult, StageStatus
from job_hunter.tools.search.base import SearchResult


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


def _valid_job_html() -> str:
    return (
        "<html><body>"
        "<h1>Engineering Manager</h1>"
        "<section>Job description with responsibilities and qualifications for software development leadership.</section>"
        "<p>Apply now to join our team.</p>"
        "</body></html>"
    ) * 3


@patch("job_hunter.agent.orchestrator.save_success_artifacts")
@patch("job_hunter.agent.orchestrator.validate_downloaded_page")
def test_agent_run_processes_posting(
    mock_validate: MagicMock,
    mock_save_artifacts: MagicMock,
    tmp_path: Path,
) -> None:
    """Agent downloads, validates, extracts, ranks, saves, and updates history."""
    config = _config(tmp_path)
    (tmp_path / "resume.md").write_text("# Resume", encoding="utf-8")
    profile = JobSearchProfile(target_titles=["Manager"])
    posting = JobPosting(
        title="Engineering Manager",
        company="Example Corp",
        location="Montreal",
        url="https://example.com/job/1",
        description="Lead software development teams with clear responsibilities and qualifications.",
    )
    posting.confidence_score = 0.95
    mock_validate.return_value = MagicMock(status=StageStatus.SUCCESS)
    mock_save_artifacts.return_value = tmp_path / "output" / "Example Corp" / "Engineering Manager" / "posting.md"

    profile_service = MagicMock()
    profile_service.load_or_generate.return_value = profile
    history = MagicMock()
    history.is_duplicate.return_value = False
    search = MagicMock()
    search.discover_urls.return_value = [SearchResult(url="https://example.com/job/1", source="serper")]
    download = MagicMock()
    download.download.return_value = _valid_job_html()
    extract = MagicMock()
    extract.extract.return_value = (posting, {"extraction_status": "SUCCESS"})
    rank = MagicMock()
    rank.should_process.return_value = (True, "")
    rank.rank.return_value = RankingResult(status=StageStatus.SUCCESS, overall_score=0.95, reason="Good fit")
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

    agent.run(options=RunOptions(test_mode=True))

    history.save.assert_called_once()
    history.add_entry.assert_called_once()
    resume.invoke.assert_called_once()


@patch("job_hunter.agent.orchestrator.validate_downloaded_page")
def test_agent_skips_invalid_download(mock_validate: MagicMock, tmp_path: Path) -> None:
    """Invalid downloaded pages are recorded and skip extraction."""
    config = _config(tmp_path)
    (tmp_path / "resume.md").write_text("# Resume", encoding="utf-8")
    profile = JobSearchProfile(target_titles=["Manager"])
    mock_validate.return_value = MagicMock(
        status=StageStatus.FAILED,
        failure_reason="Cloudflare block page",
        page_type=MagicMock(value="cloudflare_block"),
    )

    profile_service = MagicMock()
    profile_service.load_or_generate.return_value = profile
    history = MagicMock()
    search = MagicMock()
    search.discover_urls.return_value = [SearchResult(url="https://example.com/1", source="serper")]
    download = MagicMock()
    download.download.return_value = "<html>Just a moment... cloudflare challenge-platform</html>" * 20
    extract = MagicMock()
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

    agent.run(options=RunOptions(test_mode=True))

    history.add_failed_download.assert_called_once()
    extract.extract.assert_not_called()
    rank.rank.assert_not_called()
    resume.invoke.assert_not_called()


@patch("job_hunter.agent.orchestrator.validate_downloaded_page")
def test_agent_skips_duplicate(mock_validate: MagicMock, tmp_path: Path) -> None:
    """Duplicate postings update history and skip further processing."""
    config = _config(tmp_path)
    (tmp_path / "resume.md").write_text("# Resume", encoding="utf-8")
    profile = JobSearchProfile(target_titles=["Manager"])
    posting = JobPosting(
        title="Manager",
        company="Corp",
        location="Montreal",
        url="https://example.com/1",
        description="Software development leadership role with responsibilities and qualifications.",
    )
    mock_validate.return_value = MagicMock(status=StageStatus.SUCCESS)

    profile_service = MagicMock()
    profile_service.load_or_generate.return_value = profile
    history = MagicMock()
    history.is_duplicate.return_value = True
    search = MagicMock()
    search.discover_urls.return_value = [SearchResult(url="https://example.com/1", source="serper")]
    download = MagicMock()
    download.download.return_value = _valid_job_html()
    extract = MagicMock()
    extract.extract.return_value = (posting, {"extraction_status": "SUCCESS"})
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

    agent.run(options=RunOptions(test_mode=True))

    history.touch_duplicate.assert_called_once()
    rank.rank.assert_not_called()
    resume.invoke.assert_not_called()
