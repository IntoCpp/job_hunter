"""Tests for deterministic filtering."""

from job_hunter.models.job_posting import JobPosting
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.services.filtering_service import is_excluded_posting


def test_excluded_company_is_rejected() -> None:
    """Excluded companies are filtered before ranking."""
    posting = JobPosting(title="Developer", company="Bad Corp", location="Montreal", url="https://x")
    profile = JobSearchProfile(excluded_companies=["Bad Corp"])
    assert is_excluded_posting(posting, profile)


def test_excluded_title_is_rejected() -> None:
    """Excluded titles are filtered before ranking."""
    posting = JobPosting(title="Junior Intern", company="Good Corp", location="Montreal", url="https://x")
    profile = JobSearchProfile(excluded_titles=["Intern"])
    assert is_excluded_posting(posting, profile)
