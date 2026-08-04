"""Pipeline stage status and validation result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StageStatus(str, Enum):
    """Outcome of a pipeline stage."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PageType(str, Enum):
    """Classification of a downloaded web page."""

    VALID_JOB_POSTING = "valid_job_posting"
    SEARCH_RESULTS = "search_results"
    CLOUDFLARE_BLOCK = "cloudflare_block"
    CAPTCHA = "captcha"
    LOGIN_PAGE = "login_page"
    ACCESS_DENIED = "access_denied"
    ERROR_PAGE = "error_page"
    UNKNOWN = "unknown"


@dataclass
class DownloadValidationResult:
    """Result of validating downloaded page content."""

    status: StageStatus
    page_type: PageType
    failure_reason: str = ""


@dataclass
class ExtractionResult:
    """Result of extracting structured fields from a posting page."""

    status: StageStatus
    failure_reason: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RankingResult:
    """Result of semantic ranking for a job posting."""

    status: StageStatus
    overall_score: float | None = None
    criterion_scores: dict[str, float] = field(default_factory=dict)
    reason: str = ""
    failure_reason: str = ""
