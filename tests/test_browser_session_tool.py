"""Tests for browser session retrieval via CDP."""

from unittest.mock import MagicMock, patch

import pytest

from job_hunter.models.config import BrowserSessionBrowserConfig, BrowserSessionConfig
from job_hunter.tools.browser_session_tool import BrowserSessionTool


@patch("playwright.sync_api.sync_playwright")
def test_fetch_html_uses_cdp_connect(mock_sync_playwright: MagicMock) -> None:
    """Browser session retrieval connects to the configured CDP endpoint."""
    page = MagicMock()
    page.content.return_value = "<html>job description responsibilities qualifications apply now</html>" * 5
    context = MagicMock()
    context.new_page.return_value = page
    browser = MagicMock()
    browser.contexts = [context]
    playwright = MagicMock()
    playwright.chromium.connect_over_cdp.return_value = browser
    mock_sync_playwright.return_value.__enter__.return_value = playwright

    config = BrowserSessionConfig(debug_host="127.0.0.1", debug_port=9222)
    content = BrowserSessionTool(config).fetch_html("https://example.com/job/1")

    playwright.chromium.connect_over_cdp.assert_called_once_with("http://127.0.0.1:9222")
    page.goto.assert_called_once()
    page.close.assert_called_once()
    browser.close.assert_called_once()
    assert "job description" in content


@patch("playwright.sync_api.sync_playwright")
def test_fetch_html_falls_back_to_explicit_persistent_profile(mock_sync_playwright: MagicMock, tmp_path) -> None:
    """CDP failure falls back to an explicitly configured persistent profile."""
    page = MagicMock()
    page.content.return_value = "<html>job description responsibilities qualifications apply now</html>" * 5
    context = MagicMock()
    context.pages = []
    context.new_page.return_value = page
    playwright = MagicMock()
    playwright.chromium.connect_over_cdp.side_effect = RuntimeError("connection refused")
    playwright.chromium.launch_persistent_context.return_value = context
    mock_sync_playwright.return_value.__enter__.return_value = playwright

    profile_dir = tmp_path / "edge_profile"
    profile_dir.mkdir()
    config = BrowserSessionConfig(
        browsers=[BrowserSessionBrowserConfig(type="edge", user_data_dir=str(profile_dir))],
    )
    content = BrowserSessionTool(config).fetch_html("https://example.com/job/1")

    playwright.chromium.launch_persistent_context.assert_called_once()
    assert "job description" in content


@patch("playwright.sync_api.sync_playwright")
def test_fetch_html_raises_when_all_strategies_fail(mock_sync_playwright: MagicMock) -> None:
    """Browser session retrieval reports failure when CDP and profile fallback both fail."""
    playwright = MagicMock()
    playwright.chromium.connect_over_cdp.side_effect = RuntimeError("connection refused")
    mock_sync_playwright.return_value.__enter__.return_value = playwright

    with pytest.raises(RuntimeError, match="CDP connect failed"):
        BrowserSessionTool(BrowserSessionConfig()).fetch_html("https://example.com/job/1")
