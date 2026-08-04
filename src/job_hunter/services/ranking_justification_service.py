"""Build brief ranking justifications from criterion scores."""

from __future__ import annotations

from job_hunter.models.pipeline import RankingResult

_CRITERION_LABELS = {
    "software_relevance": "Software relevance",
    "leadership": "Leadership",
    "management": "Management",
    "location": "Location",
}


def build_ranking_justification(ranking_result: RankingResult) -> tuple[str, str]:
    """Identify the strongest and weakest ranking criteria.

    Parameters:
        ranking_result: Successful ranking result with criterion scores.

    Returns:
        Tuple of (top_matching_qualification, largest_qualification_gap).
    """
    scores = ranking_result.criterion_scores
    if not scores:
        return "", ""

    top_key = max(scores, key=lambda key: (scores[key], _criterion_sort_key(key)))
    gap_key = min(scores, key=lambda key: (scores[key], _criterion_sort_key(key)))
    top_label = _criterion_label(top_key)
    gap_label = _criterion_label(gap_key)
    return (
        f"{top_label} ({scores[top_key]:.2f})",
        f"{gap_label} ({scores[gap_key]:.2f})",
    )


def _criterion_label(key: str) -> str:
    return _CRITERION_LABELS.get(key, key.replace("_", " ").title())


def _criterion_sort_key(key: str) -> str:
    return key.casefold()
