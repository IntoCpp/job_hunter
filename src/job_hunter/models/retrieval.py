"""Job posting retrieval result models."""

from __future__ import annotations

from dataclasses import dataclass, field

from job_hunter.models.pipeline import DownloadValidationResult

RETRIEVAL_METHOD_HTTP = "http"
RETRIEVAL_METHOD_PLAYWRIGHT = "playwright"
RETRIEVAL_METHOD_BROWSER_SESSION = "browser_session"


@dataclass
class RetrievalAttempt:
    """Record of a single retrieval method attempt."""

    method: str
    success: bool
    failure_reason: str = ""
    error_details: str = ""


@dataclass
class RetrievalResult:
    """Outcome of the multi-step posting retrieval strategy."""

    success: bool
    content: str = ""
    retrieval_method: str = ""
    attempts: list[RetrievalAttempt] = field(default_factory=list)
    validation: DownloadValidationResult | None = None
    failure_reason: str = ""

    def attempted_methods(self) -> list[str]:
        """Return retrieval method identifiers in attempt order."""
        return [attempt.method for attempt in self.attempts]
