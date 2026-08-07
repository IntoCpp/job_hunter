"""Browser session retrieval fallback via CDP and optional persistent profiles."""

from __future__ import annotations

import logging
from pathlib import Path

from job_hunter.models.config import BrowserSessionBrowserConfig, BrowserSessionConfig

logger = logging.getLogger(__name__)

_SUPPORTED_BROWSER_TYPES = frozenset({"edge", "chrome"})


class BrowserSessionTool:
    """Retrieve page content by connecting to a running browser or an explicit profile."""

    def __init__(self, config: BrowserSessionConfig | None = None) -> None:
        """Initialize the browser session tool.

        Parameters:
            config: Browser session configuration.
        """
        self._config = config or BrowserSessionConfig()

    def fetch_html(self, url: str) -> str:
        """Fetch rendered HTML using CDP and optional persistent-profile fallbacks.

        Parameters:
            url: Page URL.

        Returns:
            Rendered page HTML.

        Raises:
            RuntimeError: If all browser session strategies fail.
        """
        errors: list[str] = []
        try:
            return self._fetch_via_cdp(url)
        except RuntimeError as exc:
            errors.append(f"CDP connect failed: {exc}")

        for browser in _persistent_profile_candidates(self._config):
            try:
                return self._fetch_via_persistent_profile(url, browser)
            except RuntimeError as exc:
                errors.append(f"Persistent profile ({browser.type}) failed: {exc}")

        raise RuntimeError("; ".join(errors))

    def _fetch_via_cdp(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed") from exc

        endpoint = f"http://{self._config.debug_host}:{self._config.debug_port}"
        logger.debug("Browser session CDP connect: %s", endpoint)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(endpoint)
                try:
                    context = browser.contexts[0] if browser.contexts else browser.new_context()
                    page = context.new_page()
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        return page.content()
                    finally:
                        page.close()
                finally:
                    browser.close()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def _fetch_via_persistent_profile(self, url: str, browser: BrowserSessionBrowserConfig) -> str:
        browser_type = browser.type.casefold()
        if browser_type not in _SUPPORTED_BROWSER_TYPES:
            raise RuntimeError(f"Unsupported browser session type: {browser.type}")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed") from exc

        user_data_dir = Path(browser.user_data_dir.strip())
        channel = "msedge" if browser_type == "edge" else "chrome"
        launch_kwargs: dict[str, object] = {
            "headless": True,
            "channel": channel,
        }
        if browser.executable.strip():
            launch_kwargs["executable_path"] = browser.executable.strip()

        logger.debug("Browser session persistent profile (%s): %s", browser_type, url)
        try:
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    str(user_data_dir),
                    **launch_kwargs,
                )
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    return page.content()
                finally:
                    context.close()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc


def _persistent_profile_candidates(config: BrowserSessionConfig) -> list[BrowserSessionBrowserConfig]:
    return [browser for browser in config.browsers if browser.user_data_dir.strip()]
