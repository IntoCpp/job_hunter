"""Download tool for retrieving job posting content."""

from __future__ import annotations

import logging

import httpx

from job_hunter.tools.browser_tool import BrowserTool

logger = logging.getLogger(__name__)

_MIN_CONTENT_LENGTH = 400


class DownloadTool:
    """Download job posting pages via HTTP with Playwright fallback."""

    def __init__(self, http_client: httpx.Client | None = None, browser_tool: BrowserTool | None = None) -> None:
        """Initialize download tool.

        Parameters:
            http_client: Optional shared HTTP client.
            browser_tool: Optional browser fallback tool.
        """
        self._http_client = http_client
        self._browser_tool = browser_tool or BrowserTool()

    def download(self, url: str) -> str:
        """Retrieve page content for a job posting URL.

        Parameters:
            url: Job posting URL.

        Returns:
            Retrieved HTML or text content.

        Raises:
            RuntimeError: If both HTTP and browser retrieval fail.
        """
        content = self._download_via_http(url)
        if len(content) >= _MIN_CONTENT_LENGTH:
            return content

        logger.info("HTTP content insufficient for %s, trying Playwright fallback", url)
        try:
            return self._browser_tool.fetch_html(url)
        except RuntimeError as exc:
            if content:
                logger.warning("Playwright fallback failed, using short HTTP content: %s", exc)
                return content
            raise RuntimeError(f"Failed to download content from {url}") from exc

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
