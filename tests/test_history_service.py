"""Tests for posting history service."""

from datetime import date
from pathlib import Path

from job_hunter.models.job_posting import JobPosting
from job_hunter.services.history_service import HistoryService


def _sample_posting() -> JobPosting:
    return JobPosting(
        title="Software Development Manager",
        company="Example Corp",
        location="Montreal, Quebec",
        url="https://example.com/jobs/1",
        description="Lead engineering teams.",
    )


def test_history_duplicate_detection(tmp_path: Path) -> None:
    """Duplicate postings are detected by company, title, and location."""
    history = HistoryService(tmp_path / "history.yaml")
    posting = _sample_posting()
    history.add_entry(posting, markdown_path="out/posting.md", seen_on=date(2026, 1, 1))
    assert history.is_duplicate(posting)


def test_history_touch_duplicate_updates_last_seen(tmp_path: Path) -> None:
    """Encountering a duplicate updates date_last_seen."""
    history_path = tmp_path / "history.yaml"
    history = HistoryService(history_path)
    posting = _sample_posting()
    history.add_entry(posting, markdown_path="out/posting.md", seen_on=date(2026, 1, 1))
    assert history.touch_duplicate(posting, seen_on=date(2026, 2, 1))

    history.save()
    reloaded = HistoryService(history_path)
    entry = reloaded._entries[0]
    assert entry.date_last_seen == date(2026, 2, 1)


def test_history_save_and_load_round_trip(tmp_path: Path) -> None:
    """History persists to YAML and reloads correctly."""
    history_path = tmp_path / "history.yaml"
    history = HistoryService(history_path)
    posting = _sample_posting()
    posting.confidence_score = 0.91
    history.add_entry(posting, markdown_path="out/posting.md", seen_on=date(2026, 3, 1))
    history.save()

    reloaded = HistoryService(history_path)
    assert len(reloaded._entries) == 1
    assert reloaded._entries[0].ranking_score == 0.91
