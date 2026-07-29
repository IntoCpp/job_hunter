"""Tests for posting markdown writer."""

from pathlib import Path

from job_hunter.models.job_posting import JobPosting
from job_hunter.services.posting_writer import save_posting_markdown


def test_save_posting_markdown_creates_file(tmp_path: Path) -> None:
    """Posting is saved under company/title.md."""
    posting = JobPosting(
        title="Software Manager",
        company="Example Corp",
        location="Montreal",
        url="https://example.com/job/1",
        description="Manage teams.",
        confidence_score=0.92,
    )
    saved = save_posting_markdown(posting, tmp_path)
    assert saved.exists()
    content = saved.read_text(encoding="utf-8")
    assert "Software Manager" in content
    assert "0.92" in content
