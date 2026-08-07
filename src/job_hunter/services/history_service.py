"""Posting history persistence and duplicate detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from job_hunter.models.history import PostingHistoryEntry, normalize_history_field
from job_hunter.models.job_posting import UNKNOWN_COMPANY, JobPosting
from job_hunter.models.pipeline import RankingResult
from job_hunter.services.ranking_justification_service import build_ranking_justification

logger = logging.getLogger(__name__)

_ACCEPTED_FILE = "accepted_postings.yaml"
_REJECTED_FILE = "rejected_postings.yaml"
_FAILED_DOWNLOADS_FILE = "failed_downloads.yaml"
_FAILED_EXTRACTIONS_FILE = "failed_extractions.yaml"


@dataclass
class FailureHistoryEntry:
    """Record of a failed download or extraction."""

    url: str
    date_recorded: date
    failure_reason: str
    source: str
    metadata: dict[str, str] = field(default_factory=dict)


def resolve_history_dir(history_path: Path) -> Path:
    """Resolve the history directory from configuration.

    Parameters:
        history_path: Configured history path (directory or legacy YAML file).

    Returns:
        Directory containing split history files.
    """
    if history_path.suffix.lower() in {".yaml", ".yml"}:
        return history_path.parent / "history"
    return history_path


class HistoryService:
    """Maintain processed posting history and detect duplicates."""

    def __init__(self, history_path: Path) -> None:
        """Initialize the history service.

        Parameters:
            history_path: Configured history path (directory or legacy YAML file).
        """
        self.history_dir = resolve_history_dir(history_path)
        self._legacy_path = history_path if history_path.suffix.lower() in {".yaml", ".yml"} else None
        self._accepted_path = self.history_dir / _ACCEPTED_FILE
        self._rejected_path = self.history_dir / _REJECTED_FILE
        self._failed_downloads_path = self.history_dir / _FAILED_DOWNLOADS_FILE
        self._failed_extractions_path = self.history_dir / _FAILED_EXTRACTIONS_FILE
        self._accepted: list[PostingHistoryEntry] = []
        self._rejected: list[PostingHistoryEntry] = []
        self._failed_downloads: list[FailureHistoryEntry] = []
        self._failed_extractions: list[FailureHistoryEntry] = []
        self._index: dict[tuple[str, str, str], PostingHistoryEntry] = {}
        self.load()

    def load(self) -> None:
        """Load history entries from disk when files exist."""
        self._accepted = []
        self._rejected = []
        self._failed_downloads = []
        self._failed_extractions = []
        self._index = {}
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._import_legacy_history()
        self._accepted = self._load_posting_entries(self._accepted_path)
        self._rejected = self._load_posting_entries(self._rejected_path)
        self._failed_downloads = self._load_failure_entries(self._failed_downloads_path)
        self._failed_extractions = self._load_failure_entries(self._failed_extractions_path)
        for entry in self._accepted:
            self._index[entry.duplicate_key()] = entry

    def save(self) -> None:
        """Persist all history files to disk."""
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._save_posting_entries(self._accepted_path, self._accepted)
        self._save_posting_entries(self._rejected_path, self._rejected)
        self._save_failure_entries(self._failed_downloads_path, self._failed_downloads)
        self._save_failure_entries(self._failed_extractions_path, self._failed_extractions)

    def is_duplicate(self, posting: JobPosting) -> bool:
        """Check whether a posting matches an existing accepted history entry."""
        if not posting.has_required_fields():
            return False
        return posting.duplicate_key() in self._index

    def touch_duplicate(self, posting: JobPosting, *, seen_on: date | None = None) -> bool:
        """Update date_last_seen when a duplicate posting is encountered."""
        entry = self._index.get(posting.duplicate_key())
        if entry is None:
            return False
        entry.date_last_seen = seen_on or date.today()
        logger.info("Duplicate posting updated date_last_seen: %s / %s", posting.company, posting.title)
        return True

    def add_entry(
        self,
        posting: JobPosting,
        *,
        markdown_path: str,
        ranking_result: RankingResult | None = None,
        retrieval_method: str = "",
        seen_on: date | None = None,
    ) -> None:
        """Add a newly accepted posting to history."""
        today = seen_on or date.today()
        top_match = ""
        largest_gap = ""
        if ranking_result is not None and ranking_result.criterion_scores:
            top_match, largest_gap = build_ranking_justification(ranking_result)
        entry = PostingHistoryEntry(
            company=_history_company(posting.company),
            job_title=posting.title,
            location=posting.location or "Unknown Location",
            url=posting.url,
            date_first_found=today,
            date_last_seen=today,
            ranking_score=posting.confidence_score,
            top_matching_qualification=top_match,
            largest_qualification_gap=largest_gap,
            markdown_path=markdown_path,
            metadata=_build_metadata(posting, retrieval_method=retrieval_method),
        )
        self._accepted.append(entry)
        self._index[entry.duplicate_key()] = entry

    def add_rejected(
        self,
        posting: JobPosting,
        *,
        markdown_path: str,
        rejection_reason: str,
        retrieval_method: str = "",
        seen_on: date | None = None,
    ) -> None:
        """Add a posting rejected before ranking."""
        today = seen_on or date.today()
        metadata = _build_metadata(posting, retrieval_method=retrieval_method)
        metadata["rejection_reason"] = rejection_reason
        entry = PostingHistoryEntry(
            company=_history_company(posting.company),
            job_title=posting.title or "Unknown Title",
            location=posting.location or "Unknown Location",
            url=posting.url,
            date_first_found=today,
            date_last_seen=today,
            ranking_score=None,
            markdown_path=markdown_path,
            metadata=metadata,
        )
        self._rejected.append(entry)

    def add_failed_download(
        self,
        *,
        url: str,
        failure_reason: str,
        source: str,
        page_type: str,
        company: str = "",
        retrieval_attempts: list[str] | None = None,
        error_details: str = "",
        seen_on: date | None = None,
    ) -> None:
        """Record a failed download validation."""
        metadata: dict[str, str] = {"page_type": page_type}
        if company:
            metadata["company"] = company
        if retrieval_attempts:
            metadata["retrieval_attempts"] = ",".join(retrieval_attempts)
        if error_details:
            metadata["error_details"] = error_details
        self._failed_downloads.append(
            FailureHistoryEntry(
                url=url,
                date_recorded=seen_on or date.today(),
                failure_reason=failure_reason,
                source=source,
                metadata=metadata,
            )
        )

    def add_failed_extraction(
        self,
        posting: JobPosting,
        *,
        failure_reason: str,
        artifact_path: str = "",
        seen_on: date | None = None,
    ) -> None:
        """Record a failed extraction."""
        metadata = _build_metadata(posting)
        if artifact_path:
            metadata["artifact_path"] = artifact_path
        self._failed_extractions.append(
            FailureHistoryEntry(
                url=posting.url,
                date_recorded=seen_on or date.today(),
                failure_reason=failure_reason,
                source=posting.source,
                metadata=metadata,
            )
        )

    def _import_legacy_history(self) -> None:
        if self._legacy_path is None or not self._legacy_path.exists() or self._accepted_path.exists():
            return
        with self._legacy_path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        entries = [self._entry_from_mapping(item) for item in data.get("postings", [])]
        if entries:
            self._save_posting_entries(self._accepted_path, entries)

    def _load_posting_entries(self, path: Path) -> list[PostingHistoryEntry]:
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return [self._entry_from_mapping(item) for item in data.get("postings", [])]

    def _load_failure_entries(self, path: Path) -> list[FailureHistoryEntry]:
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        entries: list[FailureHistoryEntry] = []
        for item in data.get("failures", []):
            entries.append(
                FailureHistoryEntry(
                    url=str(item.get("url", "")),
                    date_recorded=_parse_date(item.get("date")),
                    failure_reason=str(item.get("failure_reason", "")),
                    source=str(item.get("source", "")),
                    metadata={str(k): str(v) for k, v in (item.get("metadata") or {}).items()},
                )
            )
        return entries

    def _save_posting_entries(self, path: Path, entries: list[PostingHistoryEntry]) -> None:
        payload = {
            "postings": [
                _posting_entry_payload(entry)
                for entry in entries
            ]
        }
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)

    def _save_failure_entries(self, path: Path, entries: list[FailureHistoryEntry]) -> None:
        payload = {
            "failures": [
                {
                    "url": entry.url,
                    "date": entry.date_recorded.isoformat(),
                    "failure_reason": entry.failure_reason,
                    "source": entry.source,
                    "metadata": entry.metadata,
                }
                for entry in entries
            ]
        }
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)

    def _entry_from_mapping(self, item: object) -> PostingHistoryEntry:
        if not isinstance(item, dict):
            raise ValueError("History entry must be a mapping")
        return PostingHistoryEntry(
            company=str(item.get("company", "")),
            job_title=str(item.get("job_title", "")),
            location=str(item.get("location", "")),
            url=str(item.get("url", "")),
            date_first_found=_parse_date(item.get("date_first_found")),
            date_last_seen=_parse_date(item.get("date_last_seen")),
            ranking_score=item.get("ranking_score"),
            top_matching_qualification=_load_ranking_field(item, "top_matching_qualification"),
            largest_qualification_gap=_load_ranking_field(item, "largest_qualification_gap"),
            markdown_path=str(item.get("markdown_path", "")),
            metadata={str(k): str(v) for k, v in (item.get("metadata") or {}).items()},
        )


def _history_company(company: str) -> str:
    normalized = company.strip()
    if not normalized or normalized.casefold() == "none":
        return UNKNOWN_COMPANY
    return normalized


def _build_metadata(posting: JobPosting, *, retrieval_method: str = "") -> dict[str, str]:
    metadata = {
        "extraction_status": posting.extraction_status.value,
        "source": posting.source,
    }
    if retrieval_method:
        metadata["retrieval_method"] = retrieval_method
    if posting.extracted_company and posting.extracted_company != posting.company:
        metadata["extracted_company"] = posting.extracted_company
    if posting.language:
        metadata["language"] = posting.language
    if posting.extraction_failure_reason:
        metadata["extraction_failure_reason"] = posting.extraction_failure_reason
    return metadata


def _parse_date(value: object) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return date.today()


def _posting_entry_payload(entry: PostingHistoryEntry) -> dict[str, object]:
    payload: dict[str, object] = {
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
    justification = _ranking_justification_payload(entry)
    if justification is not None:
        payload["ranking_justification"] = justification
    return payload


def _ranking_justification_payload(entry: PostingHistoryEntry) -> dict[str, str] | None:
    if not entry.top_matching_qualification and not entry.largest_qualification_gap:
        return None
    return {
        "top_matching_qualification": entry.top_matching_qualification,
        "largest_qualification_gap": entry.largest_qualification_gap,
    }


def _load_ranking_field(item: dict[str, object], field_name: str) -> str:
    justification = item.get("ranking_justification")
    if isinstance(justification, dict) and field_name in justification:
        return str(justification[field_name])
    value = item.get(field_name)
    return str(value) if value is not None else ""
