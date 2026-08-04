"""Job posting domain model."""

from __future__ import annotations

from dataclasses import dataclass, field

from job_hunter.models.history import normalize_history_field
from job_hunter.models.pipeline import StageStatus

SUPPORTED_LANGUAGES = frozenset({"en", "fr"})
UNKNOWN_COMPANY = "Unknown Company"
UNKNOWN_TITLE = "Unknown Title"
UNKNOWN_LOCATION = "Unknown Location"
PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "none",
        "null",
        "unknown",
        "unknown company",
        "unknown title",
        "unknown location",
        "n/a",
        "na",
    }
)


def normalize_language(value: str) -> str:
    """Normalize a language code to a supported ISO 639-1 value.

    Parameters:
        value: Raw language value from extraction or metadata.

    Returns:
        Normalized language code (`en` or `fr`), or empty string when unknown.
    """
    normalized = value.strip().casefold()
    if normalized in {"en", "english", "anglais"}:
        return "en"
    if normalized in {"fr", "french", "français", "francais"}:
        return "fr"
    if normalized in SUPPORTED_LANGUAGES:
        return normalized
    return ""


def is_present_field(value: str | None) -> bool:
    """Return True when a field contains a usable non-placeholder value.

    Parameters:
        value: Raw field value from extraction or history.

    Returns:
        True when the value is present and not a placeholder.
    """
    if value is None:
        return False
    normalized = " ".join(str(value).strip().casefold().split())
    return normalized not in PLACEHOLDER_VALUES


@dataclass
class JobPosting:
    """Structured job posting discovered and processed by Job-Hunter."""

    title: str
    company: str
    location: str
    url: str
    description: str = ""
    address: str = ""
    language: str = ""
    confidence_score: float | None = None
    markdown_path: str = ""
    raw_content: str = field(default="", repr=False)
    extraction_status: StageStatus = StageStatus.SUCCESS
    extraction_failure_reason: str = ""
    source: str = ""
    extracted_company: str = ""

    def has_required_fields(self) -> bool:
        """Return True when company, title, and description are present."""
        return (
            is_present_field(self.company)
            and is_present_field(self.title)
            and is_present_field(self.description)
        )

    def duplicate_key(self) -> tuple[str, str, str]:
        """Return normalized key used for duplicate detection."""
        return (
            normalize_history_field(self.company),
            normalize_history_field(self.title),
            normalize_history_field(self.location),
        )
