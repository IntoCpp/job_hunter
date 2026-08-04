"""Tests for ranking justification helpers."""

from job_hunter.models.pipeline import RankingResult, StageStatus
from job_hunter.services.ranking_justification_service import build_ranking_justification


def test_build_ranking_justification_identifies_top_and_gap() -> None:
    """Justification highlights the highest and lowest criterion scores."""
    result = RankingResult(
        status=StageStatus.SUCCESS,
        overall_score=0.73,
        criterion_scores={
            "software_relevance": 0.25,
            "leadership": 0.95,
            "management": 0.90,
            "location": 1.00,
        },
        reason="Strong leadership fit.",
    )

    top_match, largest_gap = build_ranking_justification(result)

    assert top_match == "Location (1.00)"
    assert largest_gap == "Software relevance (0.25)"
