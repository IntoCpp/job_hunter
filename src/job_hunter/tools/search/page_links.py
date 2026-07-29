"""Extract job-related links from HTML pages."""

from __future__ import annotations

import re

import httpx

from job_hunter.utils.url import extract_domain

_HREF_PATTERN = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
_JOB_LINK_TOKENS = ("job", "career", "emploi", "posting", "position", "offre", "carriere")


def extract_job_links_from_html(page_url: str, html: str, domain: str) -> list[str]:
    """Extract same-domain job-related links from HTML content.

    Parameters:
        page_url: URL the HTML was fetched from (for resolving relative links).
        html: Page HTML content.
        domain: Hostname used to filter links.

    Returns:
        Absolute URLs that appear job-related.
    """
    links: list[str] = []
    seen: set[str] = set()
    for href in _HREF_PATTERN.findall(html):
        normalized = _normalize_href(page_url, href)
        if not normalized or normalized in seen:
            continue
        if domain not in extract_domain(normalized):
            continue
        if not any(token in normalized.casefold() for token in _JOB_LINK_TOKENS):
            continue
        seen.add(normalized)
        links.append(normalized)
    return links[:20]


def fetch_page_html(page_url: str, http_client: httpx.Client | None = None) -> str:
    """Fetch HTML content for a page URL.

    Parameters:
        page_url: Page to fetch.
        http_client: Optional shared HTTP client.

    Returns:
        Page HTML, or empty string on failure.
    """
    client = http_client or httpx.Client(timeout=30.0, follow_redirects=True)
    owns_client = http_client is None
    try:
        response = client.get(page_url)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError:
        return ""
    finally:
        if owns_client:
            client.close()


def _normalize_href(page_url: str, href: str) -> str:
    href = href.strip()
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        base = httpx.URL(page_url)
        return str(base.copy_with(path=href))
    return ""
