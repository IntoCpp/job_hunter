"""Tests for JobBoard configuration model."""

from job_hunter.models.config import JobBoard


def test_resolved_domain_from_explicit_domain() -> None:
    """Explicit domain is used for site-restricted search."""
    board = JobBoard(name="LinkedIn", domain="linkedin.com")
    assert board.resolved_domain() == "linkedin.com"


def test_resolved_domain_from_url() -> None:
    """Domain is derived from url when domain is omitted."""
    board = JobBoard(
        name="Hydro-Québec IT",
        url="https://emploi.hydroquebec.com/go/Technologies-information-et-communications/2661617/",
    )
    assert board.resolved_domain() == "emploi.hydroquebec.com"


def test_resolved_domain_prefers_explicit_domain() -> None:
    """Explicit domain takes precedence over url-derived domain."""
    board = JobBoard(name="Indeed", domain="ca.indeed.com", url="https://www.indeed.com/")
    assert board.resolved_domain() == "ca.indeed.com"
