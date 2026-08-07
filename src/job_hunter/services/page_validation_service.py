"""Validate downloaded pages before extraction."""

from __future__ import annotations

import re

from job_hunter.models.pipeline import DownloadValidationResult, PageType, StageStatus

_MIN_CONTENT_LENGTH = 400
_CLOUDFLARE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "just a moment",
    "attention required",
    "enable javascript and cookies",
    "checking your browser",
    "cloudflare",
)
_CAPTCHA_MARKERS = ("captcha", "hcaptcha", "recaptcha", "verify you are human", "are you a robot")
_LOGIN_MARKERS = (
    "sign in to continue",
    "log in to continue",
    "create an account to apply",
    "sign in with",
    "connexion requise",
    "veuillez vous connecter",
)
_ACCESS_DENIED_MARKERS = ("access denied", "403 forbidden", "permission denied", "accès refusé")
_ERROR_MARKERS = ("page not found", "404 not found", "something went wrong", "an error occurred")
_SEARCH_RESULTS_MARKERS = (
    "search results",
    "jobs found",
    "results for",
    "job openings near",
    "data-testid=\"jobsearch\"",
    "class=\"jobsearch",
)
_JOB_POSTING_MARKERS = (
    "job description",
    "responsibilities",
    "qualifications",
    "requirements",
    "what you'll do",
    "what you will do",
    "about the role",
    "poste",
    "responsabilités",
    "exigences",
    "apply now",
    "postuler",
)


def validate_downloaded_page(content: str) -> DownloadValidationResult:
    """Classify downloaded page content before extraction.

    Parameters:
        content: Downloaded HTML or text content.

    Returns:
        Validation result indicating whether extraction may proceed.
    """
    text = content.strip()
    if len(text) < _MIN_CONTENT_LENGTH:
        return _failed(PageType.ERROR_PAGE, "Downloaded content too short to be a job posting")

    lowered = text.casefold()

    if _matches_any(lowered, _CLOUDFLARE_MARKERS) and (
        "challenge" in lowered or "just a moment" in lowered or "cf-browser-verification" in lowered
    ):
        return _failed(PageType.CLOUDFLARE_BLOCK, "Cloudflare block page")

    if _has_usable_job_posting_content(lowered):
        return DownloadValidationResult(status=StageStatus.SUCCESS, page_type=PageType.VALID_JOB_POSTING)

    if _matches_any(lowered, _CAPTCHA_MARKERS):
        return _failed(PageType.CAPTCHA, "CAPTCHA page")

    if _matches_any(lowered, _LOGIN_MARKERS):
        return _failed(PageType.LOGIN_PAGE, "Login page")

    if _matches_any(lowered, _ACCESS_DENIED_MARKERS):
        return _failed(PageType.ACCESS_DENIED, "Access denied page")

    if _matches_any(lowered, _ERROR_MARKERS):
        return _failed(PageType.ERROR_PAGE, "Generic error page")

    if _looks_like_search_results(lowered):
        return _failed(PageType.SEARCH_RESULTS, "Search results page")

    return _failed(PageType.UNKNOWN, "Unknown page type")


def _failed(page_type: PageType, reason: str) -> DownloadValidationResult:
    return DownloadValidationResult(status=StageStatus.FAILED, page_type=page_type, failure_reason=reason)


def _matches_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _looks_like_search_results(text: str) -> bool:
    if _matches_any(text, _SEARCH_RESULTS_MARKERS):
        return True
    listing_count = len(re.findall(r"href=[\"'][^\"']*(/job|/jobs|/emploi|/career)[^\"']*[\"']", text, re.I))
    return listing_count >= 8


def _looks_like_job_posting(text: str) -> bool:
    marker_hits = sum(1 for marker in _JOB_POSTING_MARKERS if marker in text)
    return marker_hits >= 2 and len(text) >= _MIN_CONTENT_LENGTH


def _has_job_posting_structured_data(text: str) -> bool:
    """Return True when the page embeds schema.org JobPosting data."""
    return bool(re.search(r'"@type"\s*:\s*"JobPosting"', text, re.I))


def _has_usable_job_posting_content(text: str) -> bool:
    """Return True when job posting content is present despite bot-protection scripts."""
    return _looks_like_job_posting(text) or _has_job_posting_structured_data(text)
