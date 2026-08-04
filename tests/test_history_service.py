"""Tests for posting history service."""

from datetime import date
from pathlib import Path

from job_hunter.models.job_posting import JobPosting
from job_hunter.models.pipeline import RankingResult, StageStatus
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
    entry = reloaded._accepted[0]
    assert entry.date_last_seen == date(2026, 2, 1)


def test_history_save_and_load_round_trip(tmp_path: Path) -> None:
    """History persists to YAML and reloads correctly."""
    history_path = tmp_path / "history.yaml"
    history = HistoryService(history_path)
    posting = _sample_posting()
    posting.confidence_score = 0.91
    ranking_result = RankingResult(
        status=StageStatus.SUCCESS,
        overall_score=0.91,
        criterion_scores={
            "software_relevance": 0.80,
            "leadership": 0.95,
            "management": 0.88,
            "location": 0.70,
        },
        reason="Strong leadership alignment.",
    )
    history.add_entry(
        posting,
        markdown_path="out/posting.md",
        ranking_result=ranking_result,
        seen_on=date(2026, 3, 1),
    )
    history.save()

    reloaded = HistoryService(history_path)
    assert len(reloaded._accepted) == 1
    entry = reloaded._accepted[0]
    assert entry.ranking_score == 0.91
    assert entry.top_matching_qualification == "Leadership (0.95)"
    assert entry.largest_qualification_gap == "Location (0.70)"

    saved = (history_path.parent / "history" / "accepted_postings.yaml").read_text(encoding="utf-8")
    assert "ranking_justification:" in saved
    assert "top_matching_qualification:" in saved
    assert "largest_qualification_gap:" in saved
