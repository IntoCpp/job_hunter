"""Download tool for retrieving job posting content."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class DownloadTool:
    """Download job posting pages via HTTP."""

    def __init__(self, http_client: httpx.Client | None = None) -> None:
        """Initialize download tool.

        Parameters:
            http_client: Optional shared HTTP client.
        """
        self._http_client = http_client

    def download_http(self, url: str) -> str:
        """Retrieve page content for a job posting URL using HTTP.

        Parameters:
            url: Job posting URL.

        Returns:
            Retrieved HTML or text content, or an empty string on failure.
        """
        return self._download_via_http(url)

    def download(self, url: str) -> str:
        """Backward-compatible alias for HTTP retrieval.

        Parameters:
            url: Job posting URL.

        Returns:
            Retrieved HTML or text content.
        """
        return self.download_http(url)

    def _download_via_http(self, url: str) -> str:
        client = self._http_client or httpx.Client(timeout=30.0, follow_redirects=True)
        owns_client = self._http_client is None
        try:
            response = client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            logger.warning("HTTP download failed for %s: %s", url, exc)
            return ""
        finally:
            if owns_client:
                client.close()
