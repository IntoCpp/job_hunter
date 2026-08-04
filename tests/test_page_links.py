"""Tests for HTML job link extraction."""

from __future__ import annotations

from job_hunter.tools.search.page_links import _normalize_href, extract_job_links_from_html

PAGE_URL = "https://emploi.hydroquebec.com/go/Technologies-information-et-communications/2661617/"


def test_normalize_href_resolves_path_with_query_string() -> None:
    """Career pages often include tracking query parameters in href paths."""
    assert _normalize_href(PAGE_URL, "/go/offre/123?utm_source=linkedin") == (
        "https://emploi.hydroquebec.com/go/offre/123?utm_source=linkedin"
    )


def test_normalize_href_resolves_path_with_fragment() -> None:
    """Fragment identifiers must not be passed as the URL path component."""
    assert _normalize_href(PAGE_URL, "/go/offre/123#details") == (
        "https://emploi.hydroquebec.com/go/offre/123#details"
    )


def test_normalize_href_resolves_relative_path() -> None:
    """Relative job links should resolve against the source page URL."""
    assert _normalize_href(PAGE_URL, "offre/456") == (
        "https://emploi.hydroquebec.com/go/Technologies-information-et-communications/2661617/offre/456"
    )


def test_normalize_href_skips_non_navigational_links() -> None:
    """Non-http links should be ignored instead of crashing discovery."""
    assert _normalize_href(PAGE_URL, "#section") == ""
    assert _normalize_href(PAGE_URL, "javascript:void(0)") == ""
    assert _normalize_href(PAGE_URL, "mailto:jobs@example.com") == ""


def test_extract_job_links_from_html_handles_mixed_hrefs() -> None:
    """One malformed or unusual href must not abort extraction for the page."""
    html = """
    <html>
      <body>
        <a href="/go/offre/1?utm_source=linkedin">Job 1</a>
        <a href="/go/offre/2#details">Job 2</a>
        <a href="offre/3">Job 3</a>
        <a href="javascript:void(0)">Ignore</a>
        <a href="https://other.com/careers/remote">External</a>
      </body>
    </html>
    """
    links = extract_job_links_from_html(PAGE_URL, html, "emploi.hydroquebec.com")

    assert links == [
        "https://emploi.hydroquebec.com/go/offre/1?utm_source=linkedin",
        "https://emploi.hydroquebec.com/go/offre/2#details",
        "https://emploi.hydroquebec.com/go/Technologies-information-et-communications/2661617/offre/3",
    ]
