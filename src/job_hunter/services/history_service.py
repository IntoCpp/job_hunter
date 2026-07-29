"""Posting history persistence and duplicate detection."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import yaml

from job_hunter.models.history import PostingHistoryEntry, normalize_history_field
from job_hunter.models.job_posting import JobPosting

logger = logging.getLogger(__name__)


class HistoryService:
    """Maintain processed posting history and detect duplicates."""

    def __init__(self, history_path: Path) -> None:
        """Initialize the history service.

        Parameters:
            history_path: Path to the YAML history file.
        """
        self.history_path = history_path
        self._entries: list[PostingHistoryEntry] = []
        self._index: dict[tuple[str, str, str], PostingHistoryEntry] = {}
        self.load()

    def load(self) -> None:
        """Load history entries from disk when the file exists."""
        self._entries = []
        self._index = {}
        if not self.history_path.exists():
            return

        with self.history_path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        for item in data.get("postings", []):
            entry = PostingHistoryEntry(
                company=str(item.get("company", "")),
                job_title=str(item.get("job_title", "")),
                location=str(item.get("location", "")),
                url=str(item.get("url", "")),
                date_first_found=_parse_date(item.get("date_first_found")),
                date_last_seen=_parse_date(item.get("date_last_seen")),
                ranking_score=item.get("ranking_score"),
                markdown_path=str(item.get("markdown_path", "")),
                metadata={str(k): str(v) for k, v in (item.get("metadata") or {}).items()},
            )
            self._entries.append(entry)
            self._index[entry.duplicate_key()] = entry

    def save(self) -> None:
        """Persist history entries to disk."""
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "postings": [
                {
                    "company": entry.company,
                    "job_title": entry.job_title,
                    "location": entry.location,
                    "url": entry.url,
                    "date_first_found": entry.date_first_found.isoformat(),
                    "date_last_seen": entry.date_last_seen.isoformat(),
                    "ranking_score": entry.ranking_score,
                    "markdown_path": entry.markdown_path,
                    "metadata": entry.metadata,
                }
                for entry in self._entries
            ]
        }
        with self.history_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)

    def is_duplicate(self, posting: JobPosting) -> bool:
        """Check whether a posting matches an existing history entry.

        Parameters:
            posting: Job posting with company, title, and location.

        Returns:
            True if a duplicate exists.
        """
        key = (
            normalize_history_field(posting.company),
            normalize_history_field(posting.title),
            normalize_history_field(posting.location),
        )
        return key in self._index

    def touch_duplicate(self, posting: JobPosting, *, seen_on: date | None = None) -> bool:
        """Update date_last_seen when a duplicate posting is encountered.

        Parameters:
            posting: Job posting to match against history.
            seen_on: Date to record; defaults to today.

        Returns:
            True if a duplicate was found and updated.
        """
        key = (
            normalize_history_field(posting.company),
            normalize_history_field(posting.title),
            normalize_history_field(posting.location),
        )
        entry = self._index.get(key)
        if entry is None:
            return False
        entry.date_last_seen = seen_on or date.today()
        logger.info("Duplicate posting updated date_last_seen: %s / %s", posting.company, posting.title)
        return True

    def add_entry(self, posting: JobPosting, *, markdown_path: str, seen_on: date | None = None) -> None:
        """Add a newly processed posting to history.

        Parameters:
            posting: Processed posting.
            markdown_path: Saved markdown file path.
            seen_on: Date to record; defaults to today.
        """
        today = seen_on or date.today()
        entry = PostingHistoryEntry(
            company=posting.company,
            job_title=posting.title,
            location=posting.location,
            url=posting.url,
            date_first_found=today,
            date_last_seen=today,
            ranking_score=posting.confidence_score,
            markdown_path=markdown_path,
        )
        self._entries.append(entry)
        self._index[entry.duplicate_key()] = entry


def _parse_date(value: object) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return date.today()
