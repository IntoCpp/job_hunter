"""Multi-step job posting retrieval with validation-aware fallbacks."""

from __future__ import annotations

import logging

from job_hunter.models.config import BrowserSessionConfig
from job_hunter.models.pipeline import StageStatus
from job_hunter.models.retrieval import (
    RETRIEVAL_METHOD_BROWSER_SESSION,
    RETRIEVAL_METHOD_HTTP,
    RETRIEVAL_METHOD_PLAYWRIGHT,
    RetrievalAttempt,
    RetrievalResult,
)
from job_hunter.services.page_validation_service import validate_downloaded_page
from job_hunter.tools.browser_session_tool import BrowserSessionTool
from job_hunter.tools.browser_tool import BrowserTool
from job_hunter.tools.download_tool import DownloadTool

logger = logging.getLogger(__name__)


class PostingRetrievalService:
    """Retrieve job posting pages using HTTP, Playwright, and browser session fallbacks."""

    def __init__(
        self,
        browser_session_config: BrowserSessionConfig | None = None,
        *,
        download_tool: DownloadTool | None = None,
        browser_tool: BrowserTool | None = None,
        browser_session_tool: BrowserSessionTool | None = None,
    ) -> None:
        """Initialize retrieval service dependencies.

        Parameters:
            browser_session_config: Optional browser session fallback configuration.
            download_tool: Optional HTTP download tool.
            browser_tool: Optional Playwright fallback tool.
            browser_session_tool: Optional browser session fallback tool.
        """
        self._browser_session_config = browser_session_config or BrowserSessionConfig()
        self._download_tool = download_tool or DownloadTool()
        self._browser_tool = browser_tool or BrowserTool()
        self._browser_session_tool = browser_session_tool or BrowserSessionTool(self._browser_session_config)

    def retrieve(self, url: str) -> RetrievalResult:
        """Retrieve and validate job posting content using progressive fallbacks.

        Parameters:
            url: Job posting URL.

        Returns:
            Retrieval result including content and method when successful.
        """
        attempts: list[RetrievalAttempt] = []
        last_content = ""

        http_content, http_error = self._try_http(url)
        if http_content:
            last_content = http_content
            validation = validate_downloaded_page(http_content)
            if validation.status == StageStatus.SUCCESS:
                attempts.append(RetrievalAttempt(RETRIEVAL_METHOD_HTTP, True))
                return RetrievalResult(
                    success=True,
                    content=http_content,
                    retrieval_method=RETRIEVAL_METHOD_HTTP,
                    attempts=attempts,
                    validation=validation,
                )
            attempts.append(
                RetrievalAttempt(
                    RETRIEVAL_METHOD_HTTP,
                    False,
                    failure_reason=validation.failure_reason,
                    error_details=validation.page_type.value,
                )
            )
        else:
            attempts.append(
                RetrievalAttempt(
                    RETRIEVAL_METHOD_HTTP,
                    False,
                    failure_reason="HTTP request failed",
                    error_details=http_error,
                )
            )

        playwright_content, playwright_error = self._try_playwright(url)
        if playwright_content:
            last_content = playwright_content
            validation = validate_downloaded_page(playwright_content)
            if validation.status == StageStatus.SUCCESS:
                attempts.append(RetrievalAttempt(RETRIEVAL_METHOD_PLAYWRIGHT, True))
                return RetrievalResult(
                    success=True,
                    content=playwright_content,
                    retrieval_method=RETRIEVAL_METHOD_PLAYWRIGHT,
                    attempts=attempts,
                    validation=validation,
                )
            attempts.append(
                RetrievalAttempt(
                    RETRIEVAL_METHOD_PLAYWRIGHT,
                    False,
                    failure_reason=validation.failure_reason,
                    error_details=validation.page_type.value,
                )
            )
        else:
            attempts.append(
                RetrievalAttempt(
                    RETRIEVAL_METHOD_PLAYWRIGHT,
                    False,
                    failure_reason="Playwright retrieval failed",
                    error_details=playwright_error,
                )
            )

        session_content, session_error = self._try_browser_session(url)
        if session_content:
            last_content = session_content
            validation = validate_downloaded_page(session_content)
            if validation.status == StageStatus.SUCCESS:
                attempts.append(RetrievalAttempt(RETRIEVAL_METHOD_BROWSER_SESSION, True))
                return RetrievalResult(
                    success=True,
                    content=session_content,
                    retrieval_method=RETRIEVAL_METHOD_BROWSER_SESSION,
                    attempts=attempts,
                    validation=validation,
                )
            attempts.append(
                RetrievalAttempt(
                    RETRIEVAL_METHOD_BROWSER_SESSION,
                    False,
                    failure_reason=validation.failure_reason,
                    error_details=validation.page_type.value,
                )
            )
        else:
            attempts.append(
                RetrievalAttempt(
                    RETRIEVAL_METHOD_BROWSER_SESSION,
                    False,
                    failure_reason="Browser session retrieval failed",
                    error_details=session_error,
                )
            )

        failure_reason = _build_failure_reason(attempts)
        logger.info("All retrieval methods failed for %s: %s", url, failure_reason)
        return RetrievalResult(
            success=False,
            content=last_content,
            attempts=attempts,
            validation=None,
            failure_reason=failure_reason,
        )

    def _try_http(self, url: str) -> tuple[str, str]:
        try:
            content = self._download_tool.download_http(url)
        except RuntimeError as exc:
            return "", str(exc)
        if content:
            return content, ""
        return "", "Empty HTTP response"

    def _try_playwright(self, url: str) -> tuple[str, str]:
        try:
            return self._browser_tool.fetch_html(url), ""
        except RuntimeError as exc:
            return "", str(exc)

    def _try_browser_session(self, url: str) -> tuple[str, str]:
        try:
            return self._browser_session_tool.fetch_html(url), ""
        except RuntimeError as exc:
            return "", str(exc)


def _build_failure_reason(attempts: list[RetrievalAttempt]) -> str:
    reasons = [attempt.failure_reason for attempt in attempts if attempt.failure_reason]
    if reasons:
        return reasons[-1]
    return "All retrieval methods failed"
