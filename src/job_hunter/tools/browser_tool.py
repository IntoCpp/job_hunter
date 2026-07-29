"""Playwright browser automation fallback."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class BrowserTool:
    """Retrieve page content using Playwright when HTTP is insufficient."""

    def fetch_html(self, url: str) -> str:
        """Fetch rendered HTML for a URL using Playwright.

        Parameters:
            url: Page URL.

        Returns:
            Rendered page HTML.

        Raises:
            RuntimeError: If Playwright is unavailable or fetch fails.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed") from exc

        logger.debug("Playwright fetch: %s", url)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                return page.content()
            finally:
                browser.close()
