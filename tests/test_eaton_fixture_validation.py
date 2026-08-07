"""Regression test using saved Eaton posting HTML."""

from pathlib import Path

import pytest

from job_hunter.models.pipeline import PageType, StageStatus
from job_hunter.services.page_validation_service import validate_downloaded_page

_EATON_HTML = Path(
    r"C:\Users\ERIC\Documents\job_hunter_finds\failed_downloads"
    r"\https_eaton_eightfold_ai_careers_job_domain_eaton_com_utm_source_position_notification_candidate_profile_type_candidate_"
    r"\raw_download.html"
)


@pytest.mark.skipif(not _EATON_HTML.exists(), reason="Eaton fixture HTML not available on this machine")
def test_validate_saved_eaton_posting_html() -> None:
    """Saved Eaton HTML with embedded reCAPTCHA should pass download validation."""
    result = validate_downloaded_page(_EATON_HTML.read_text(encoding="utf-8"))
    assert result.status == StageStatus.SUCCESS
    assert result.page_type == PageType.VALID_JOB_POSTING
