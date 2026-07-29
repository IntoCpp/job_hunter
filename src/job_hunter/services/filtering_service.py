"""Deterministic filtering helpers for ranking workflow."""

from __future__ import annotations

from job_hunter.models.config import LocationConfig
from job_hunter.models.job_posting import JobPosting
from job_hunter.models.job_search_preferences import JobSearchPreferences
from job_hunter.models.job_search_profile import JobSearchProfile


def is_excluded_posting(
    posting: JobPosting,
    profile: JobSearchProfile,
    preferences: JobSearchPreferences | None = None,
) -> bool:
    """Check whether a posting matches excluded companies or titles.

    Parameters:
        posting: Extracted posting.
        profile: Job search profile with exclusions.
        preferences: Optional user-maintained job search preferences.

    Returns:
        True when the posting should be rejected before LLM ranking.
    """
    company = posting.company.casefold()
    title = posting.title.casefold()
    for excluded_company in profile.excluded_companies:
        if excluded_company.casefold() in company:
            return True
    for excluded_title in profile.excluded_titles:
        if excluded_title.casefold() in title:
            return True
    if preferences is not None:
        for excluded_title in preferences.excluded_titles():
            if excluded_title.casefold() in title:
                return True
    return False


def build_location_context(locations: list[LocationConfig]) -> str:
    """Serialize configured locations for LLM interpretation.

    Parameters:
        locations: Configured acceptable locations.

    Returns:
        Human-readable location context string.
    """
    lines = [f"- {item.name}: {item.guidance}" for item in locations]
    return "\n".join(lines)
