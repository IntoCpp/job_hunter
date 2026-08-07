"""Tests for multi-step posting retrieval."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from job_hunter.models.config import BrowserSessionConfig
from job_hunter.models.pipeline import PageType, StageStatus
from job_hunter.models.retrieval import (
    RETRIEVAL_METHOD_BROWSER_SESSION,
    RETRIEVAL_METHOD_HTTP,
    RETRIEVAL_METHOD_PLAYWRIGHT,
)
from job_hunter.services.retrieval_service import PostingRetrievalService


def _valid_job_html() -> str:
    return (
        "<html><body>"
        "<h1>Software Development Manager</h1>"
        "<section>Job description with responsibilities and qualifications for software development leadership.</section>"
        "<p>Apply now to join our team.</p>"
        "</body></html>"
    ) * 3


def _blocked_html() -> str:
    return "<html><body>Just a moment... challenge-platform cf-browser-verification</body></html>" * 20


def _service(
    *,
    download_tool: MagicMock | None = None,
    browser_tool: MagicMock | None = None,
    browser_session_tool: MagicMock | None = None,
) -> PostingRetrievalService:
    return PostingRetrievalService(
        BrowserSessionConfig(),
        download_tool=download_tool or MagicMock(),
        browser_tool=browser_tool or MagicMock(),
        browser_session_tool=browser_session_tool or MagicMock(),
    )


def test_http_retrieval_succeeds() -> None:
    """HTTP retrieval succeeds when content passes validation."""
    download = MagicMock()
    download.download_http.return_value = _valid_job_html()
    browser = MagicMock()
    session = MagicMock()

    result = _service(download_tool=download, browser_tool=browser, browser_session_tool=session).retrieve(
        "https://example.com/job/1"
    )

    assert result.success is True
    assert result.retrieval_method == RETRIEVAL_METHOD_HTTP
    assert result.attempted_methods() == [RETRIEVAL_METHOD_HTTP]
    browser.fetch_html.assert_not_called()
    session.fetch_html.assert_not_called()


def test_playwright_fallback_succeeds_when_http_fails() -> None:
    """Playwright succeeds when HTTP returns blocked content."""
    download = MagicMock()
    download.download_http.return_value = _blocked_html()
    browser = MagicMock()
    browser.fetch_html.return_value = _valid_job_html()
    session = MagicMock()

    result = _service(download_tool=download, browser_tool=browser, browser_session_tool=session).retrieve(
        "https://example.com/job/1"
    )

    assert result.success is True
    assert result.retrieval_method == RETRIEVAL_METHOD_PLAYWRIGHT
    assert result.attempted_methods() == [RETRIEVAL_METHOD_HTTP, RETRIEVAL_METHOD_PLAYWRIGHT]
    browser.fetch_html.assert_called_once()
    session.fetch_html.assert_not_called()


def test_browser_session_fallback_succeeds_when_http_and_playwright_fail() -> None:
    """Browser session succeeds when HTTP and Playwright both fail."""
    download = MagicMock()
    download.download_http.return_value = _blocked_html()
    browser = MagicMock()
    browser.fetch_html.return_value = _blocked_html()
    session = MagicMock()
    session.fetch_html.return_value = _valid_job_html()

    result = _service(download_tool=download, browser_tool=browser, browser_session_tool=session).retrieve(
        "https://example.com/job/1"
    )

    assert result.success is True
    assert result.retrieval_method == RETRIEVAL_METHOD_BROWSER_SESSION
    assert RETRIEVAL_METHOD_BROWSER_SESSION in result.attempted_methods()
    session.fetch_html.assert_called_once_with("https://example.com/job/1")


def test_all_retrieval_methods_fail() -> None:
    """All retrieval methods fail and record every attempt."""
    download = MagicMock()
    download.download_http.return_value = _blocked_html()
    browser = MagicMock()
    browser.fetch_html.return_value = _blocked_html()
    session = MagicMock()
    session.fetch_html.side_effect = RuntimeError("CDP connect failed")

    result = _service(download_tool=download, browser_tool=browser, browser_session_tool=session).retrieve(
        "https://example.com/job/1"
    )

    assert result.success is False
    assert result.retrieval_method == ""
    assert result.attempted_methods().count(RETRIEVAL_METHOD_HTTP) == 1
    assert result.attempted_methods().count(RETRIEVAL_METHOD_PLAYWRIGHT) == 1
    assert result.attempted_methods().count(RETRIEVAL_METHOD_BROWSER_SESSION) == 1
    assert result.failure_reason


@patch("job_hunter.agent.orchestrator.load_job_postings")
def test_orchestrator_records_failed_retrieval_and_prints_summary(
    mock_load_jobs: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Processing continues, failure history is recorded, and CLI summary is displayed."""
    from job_hunter.agent.orchestrator import JobHunterAgent, RunOptions
    from job_hunter.models.config import (
        AppConfig,
        BrowserSessionConfig,
        JobSearchPreferencesConfig,
        ModelConfig,
        ResumeReworkConfig,
        SearchProfileConfig,
    )
    from job_hunter.models.job_search_profile import JobSearchProfile
    from job_hunter.models.job_to_process import JobToProcess
    from job_hunter.models.retrieval import RetrievalAttempt, RetrievalResult
    from job_hunter.services.history_service import HistoryService

    prefs_file = tmp_path / "my_job_preferences.yaml"
    prefs_file.write_text("preferred_roles: []\nacceptable_roles: []\nexcluded_roles: []\n", encoding="utf-8")
    config = AppConfig(
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
    (tmp_path / "resume.md").write_text("# Resume", encoding="utf-8")
    mock_load_jobs.return_value = [JobToProcess(company="Example Corp", url="https://example.com/job/1")]

    profile_service = MagicMock()
    profile_service.load_or_generate.return_value = JobSearchProfile(target_titles=["Manager"])
    history = HistoryService(config.posting_history)
    retrieval = MagicMock()
    retrieval.retrieve.return_value = RetrievalResult(
        success=False,
        content=_blocked_html(),
        attempts=[
            RetrievalAttempt(RETRIEVAL_METHOD_HTTP, False, failure_reason="Cloudflare block page"),
            RetrievalAttempt(RETRIEVAL_METHOD_PLAYWRIGHT, False, failure_reason="Cloudflare block page"),
            RetrievalAttempt(RETRIEVAL_METHOD_BROWSER_SESSION, False, failure_reason="Cloudflare block page"),
        ],
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

    result = agent.run(options=RunOptions(test_mode=True))

    assert len(result.failed_retrieval_paths) == 1
    assert history._failed_downloads
    assert "retrieval_attempts" in history._failed_downloads[0].metadata
    extract.extract.assert_not_called()
    captured = capsys.readouterr()
    assert "WARNING: 1 job postings failed retrieval." in captured.out
    assert "https://example.com/job/1" not in captured.out or str(result.failed_retrieval_paths[0]) in captured.out
