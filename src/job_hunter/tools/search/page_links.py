"""Extract job-related links from HTML pages."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx

from job_hunter.utils.url import extract_domain

_HREF_PATTERN = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
_JOB_LINK_TOKENS = ("job", "career", "emploi", "posting", "position", "offre", "carriere")
_SKIP_HREF_PREFIXES = ("javascript:", "mailto:", "tel:", "data:")


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
    """Resolve an href attribute to an absolute http(s) URL.

    Parameters:
        page_url: URL the HTML was fetched from.
        href: Raw href attribute value.

    Returns:
        Absolute URL, or empty string when the href should be skipped.
    """
    href = href.strip()
    if not href or href.startswith("#"):
        return ""
    if href.casefold().startswith(_SKIP_HREF_PREFIXES):
        return ""

    try:
        if href.startswith(("http://", "https://")):
            normalized = href
        else:
            normalized = urljoin(page_url, href)
        parsed = urlparse(normalized)
        if parsed.scheme not in ("http", "https"):
            return ""
        return normalized
    except (ValueError, TypeError):
        return ""
