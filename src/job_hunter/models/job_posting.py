"""Job posting domain model."""

from __future__ import annotations

from dataclasses import dataclass, field

SUPPORTED_LANGUAGES = frozenset({"en", "fr"})


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
