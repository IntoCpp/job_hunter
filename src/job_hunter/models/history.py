"""Posting history models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class PostingHistoryEntry:
    """Record of a previously processed job posting."""

    company: str
    job_title: str
    location: str
    url: str
    date_first_found: date
    date_last_seen: date
    ranking_score: float | None = None
    top_matching_qualification: str = ""
    largest_qualification_gap: str = ""
    markdown_path: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def duplicate_key(self) -> tuple[str, str, str]:
        """Return normalized key used for duplicate detection."""
        return (
            normalize_history_field(self.company),
            normalize_history_field(self.job_title),
            normalize_history_field(self.location),
        )


def normalize_history_field(value: str) -> str:
    """Normalize a history field for duplicate comparison."""
    return " ".join(value.casefold().split())
