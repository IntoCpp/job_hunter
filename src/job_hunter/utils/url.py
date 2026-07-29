"""URL parsing helpers."""

from __future__ import annotations

from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    """Extract hostname from a URL.

    Parameters:
        url: Source URL.

    Returns:
        Lowercase hostname without leading www.
    """
    hostname = urlparse(url).hostname or ""
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname.lower()
