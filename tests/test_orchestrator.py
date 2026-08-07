"""Tests for JobHunter agent orchestration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from job_hunter.agent.orchestrator import JobHunterAgent, RunOptions
from job_hunter.models.config import (
    AppConfig,
    BrowserSessionConfig,
    JobSearchPreferencesConfig,
    ModelConfig,
    ResumeReworkConfig,
    SearchProfileConfig,
)
from job_hunter.models.job_posting import JobPosting
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.models.job_to_process import USER_INPUT_SOURCE, JobToProcess
from job_hunter.models.pipeline import RankingResult, StageStatus
from job_hunter.models.retrieval import RetrievalResult


def _config(tmp_path: Path) -> AppConfig:
    prefs_file = tmp_path / "my_job_preferences.yaml"
    prefs_file.write_text("preferred_roles: []\nacceptable_roles: []\nexcluded_roles: []\n", encoding="utf-8")
    return AppConfig(
        posting_output=tmp_path / "output",
        posting_history=tmp_path / "history.yaml",
        job_postings_file=Path("tests/test_data/sample_jobs_to_process.yaml"),
        search_profile=SearchProfileConfig(
            input_files=[tmp_path / "resume.md"],
            output_file=tmp_path / "profile.yaml",
            job_search_preferences=JobSearchPreferencesConfig(file=prefs_file),
        ),
        resume_rework=ResumeReworkConfig(script_path=tmp_path / "resume_rework.py", working_directory=tmp_path),
        confidence_resume=0.9,
        models=ModelConfig("profile", "ranking", "location", "extraction"),
        locations=[],
        browser_session=BrowserSessionConfig(),
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


def _sample_job() -> JobToProcess:
    return JobToProcess(company="Example Corp", url="https://example.com/job/1")


@patch("job_hunter.agent.orchestrator.load_job_postings")
@patch("job_hunter.agent.orchestrator.save_success_artifacts")
def test_agent_run_processes_posting(
    mock_save_artifacts: MagicMock,
    mock_load_jobs: MagicMock,
    tmp_path: Path,
) -> None:
    """Agent retrieves, extracts, ranks, saves, and updates history."""
    config = _config(tmp_path)
    (tmp_path / "resume.md").write_text("# Resume", encoding="utf-8")
    profile = JobSearchProfile(target_titles=["Manager"])
    posting = JobPosting(
        title="Engineering Manager",
        company="Example Corp",
        location="Montreal",
        url="https://example.com/job/1",
        description="Lead software development teams with clear responsibilities and qualifications.",
        source=USER_INPUT_SOURCE,
    )
    posting.confidence_score = 0.95
    mock_load_jobs.return_value = [_sample_job()]
    mock_save_artifacts.return_value = tmp_path / "output" / "Example Corp" / "Engineering Manager" / "posting.md"

    profile_service = MagicMock()
    profile_service.load_or_generate.return_value = profile
    history = MagicMock()
    history.is_duplicate.return_value = False
    retrieval = MagicMock()
    retrieval.retrieve.return_value = RetrievalResult(
        success=True,
        content=_valid_job_html(),
        retrieval_method="http",
    )
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
        retrieval_service=retrieval,
        extraction_tool=extract,
        ranking_tool=rank,
        resume_tool=resume,
    )

    agent.run(options=RunOptions(test_mode=True))

    history.save.assert_called_once()
    history.add_entry.assert_called_once()
    extract.extract.assert_called_once_with(
        url="https://example.com/job/1",
        content=retrieval.retrieve.return_value.content,
        user_company="Example Corp",
        source=USER_INPUT_SOURCE,
    )
    resume.invoke.assert_called_once()


@patch("job_hunter.agent.orchestrator.load_job_postings")
def test_agent_skips_failed_retrieval(
    mock_load_jobs: MagicMock,
    tmp_path: Path,
) -> None:
    """Failed retrieval is recorded and extraction is skipped."""
    config = _config(tmp_path)
    (tmp_path / "resume.md").write_text("# Resume", encoding="utf-8")
    profile = JobSearchProfile(target_titles=["Manager"])
    mock_load_jobs.return_value = [_sample_job()]

    profile_service = MagicMock()
    profile_service.load_or_generate.return_value = profile
    history = MagicMock()
    retrieval = MagicMock()
    retrieval.retrieve.return_value = RetrievalResult(
        success=False,
        content="<html>blocked</html>",
        attempts=[],
        failure_reason="Cloudflare block page",
    )
    extract = MagicMock()
    rank = MagicMock()
    resume = MagicMock()

    agent = JobHunterAgent(
        config,
        profile_service=profile_service,
        history_service=history,
        retrieval_service=retrieval,
        extraction_tool=extract,
        ranking_tool=rank,
        resume_tool=resume,
    )

    agent.run(options=RunOptions(test_mode=True))

    history.add_failed_download.assert_called_once()
    extract.extract.assert_not_called()
    rank.rank.assert_not_called()
    resume.invoke.assert_not_called()


@patch("job_hunter.agent.orchestrator.load_job_postings")
def test_agent_skips_duplicate(
    mock_load_jobs: MagicMock,
    tmp_path: Path,
) -> None:
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
        source=USER_INPUT_SOURCE,
    )
    mock_load_jobs.return_value = [JobToProcess(company="Corp", url="https://example.com/1")]
    retrieval = MagicMock()
    retrieval.retrieve.return_value = RetrievalResult(
        success=True,
        content=_valid_job_html(),
        retrieval_method="http",
    )

    profile_service = MagicMock()
    profile_service.load_or_generate.return_value = profile
    history = MagicMock()
    history.is_duplicate.return_value = True
    extract = MagicMock()
    extract.extract.return_value = (posting, {"extraction_status": "SUCCESS"})
    rank = MagicMock()
    resume = MagicMock()

    agent = JobHunterAgent(
        config,
        profile_service=profile_service,
        history_service=history,
        retrieval_service=retrieval,
        extraction_tool=extract,
        ranking_tool=rank,
        resume_tool=resume,
    )

    agent.run(options=RunOptions(test_mode=True))

    history.touch_duplicate.assert_called_once()
    rank.rank.assert_not_called()
    resume.invoke.assert_not_called()
