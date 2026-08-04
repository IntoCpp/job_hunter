"""Tests for downloaded page validation."""

from job_hunter.models.pipeline import PageType, StageStatus
from job_hunter.services.page_validation_service import validate_downloaded_page


def _job_posting_html() -> str:
    return (
        "<html><body>"
        "<h1>Software Development Manager</h1>"
        "<section>Job description with responsibilities and qualifications.</section>"
        "<p>Apply now for this software development leadership role.</p>"
        "</body></html>"
    ) * 5


def test_validate_downloaded_page_accepts_job_posting() -> None:
    """Valid job posting pages pass download validation."""
    result = validate_downloaded_page(_job_posting_html())
    assert result.status == StageStatus.SUCCESS
    assert result.page_type == PageType.VALID_JOB_POSTING


def test_validate_downloaded_page_rejects_cloudflare_block() -> None:
    """Cloudflare challenge pages fail download validation."""
    html = "<html><body>Just a moment... challenge-platform cf-browser-verification</body></html>" * 20
    result = validate_downloaded_page(html)
    assert result.status == StageStatus.FAILED
    assert result.page_type == PageType.CLOUDFLARE_BLOCK


def test_validate_downloaded_page_rejects_search_results_page() -> None:
    """Search results pages fail download validation."""
    links = "".join(f'<a href="/jobs/{index}">Job {index}</a>' for index in range(12))
    html = f"<html><body><h1>Search results</h1>{links}" + (" listing " * 200) + "</body></html>"
    result = validate_downloaded_page(html)
    assert result.status == StageStatus.FAILED
    assert result.page_type in {PageType.SEARCH_RESULTS, PageType.UNKNOWN}
