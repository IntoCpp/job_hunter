"""Persist posting artifacts for debugging and review."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from job_hunter.models.job_posting import JobPosting
from job_hunter.models.pipeline import RankingResult
from job_hunter.utils.path_sanitize import sanitize_path_component


def save_success_artifacts(
    posting_output: Path,
    posting: JobPosting,
    *,
    raw_html: str,
    extraction_data: dict[str, Any],
    ranking_data: dict[str, Any],
    retrieval_method: str = "",
) -> Path:
    """Save artifacts for a successfully ranked posting.

    Parameters:
        posting_output: Root output directory.
        posting: Ranked posting.
        raw_html: Downloaded page content.
        extraction_data: Extraction JSON payload.
        ranking_data: Ranking JSON payload.

    Returns:
        Path to the saved posting markdown file.
    """
    folder = _artifact_folder(posting_output, posting.company, posting.title)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "resume").mkdir(exist_ok=True)
    (folder / "raw_download.html").write_text(raw_html, encoding="utf-8")
    _write_json(folder / "extraction.json", extraction_data)
    _write_json(folder / "ranking.json", ranking_data)
    if retrieval_method:
        _write_json(folder / "retrieval.json", {"retrieval_method": retrieval_method})
    markdown_path = folder / "posting.md"
    markdown_path.write_text(_format_posting_markdown(posting), encoding="utf-8")
    return markdown_path


def save_failed_download_artifacts(
    posting_output: Path,
    *,
    url: str,
    raw_html: str,
    failure_reason: str,
    page_type: str,
    source: str,
    company: str = "",
    retrieval_attempts: list[str] | None = None,
    error_details: str = "",
) -> Path:
    """Save artifacts for a failed download validation.

    Parameters:
        posting_output: Root output directory.
        url: Source URL.
        raw_html: Downloaded page content.
        failure_reason: Human-readable failure reason.
        page_type: Page classification.
        source: Search source identifier.

    Returns:
        Path to the failure artifact directory.
    """
    folder = posting_output / "failed_downloads" / _url_folder_name(url)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "raw_download.html").write_text(raw_html, encoding="utf-8")
    _write_json(
        folder / "validation.json",
        {
            "url": url,
            "company": company,
            "failure_reason": failure_reason,
            "page_type": page_type,
            "source": source,
            "retrieval_attempts": retrieval_attempts or [],
            "error_details": error_details,
        },
    )
    return folder


def save_failed_extraction_artifacts(
    posting_output: Path,
    *,
    url: str,
    raw_html: str,
    extraction_data: dict[str, Any],
    source: str,
) -> Path:
    """Save artifacts for a failed extraction.

    Parameters:
        posting_output: Root output directory.
        url: Source URL.
        raw_html: Downloaded page content.
        extraction_data: Extraction JSON payload including status fields.
        source: Search source identifier.

    Returns:
        Path to the failure artifact directory.
    """
    folder = posting_output / "failed_extractions" / _url_folder_name(url)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "raw_download.html").write_text(raw_html, encoding="utf-8")
    payload = dict(extraction_data)
    payload.setdefault("url", url)
    payload.setdefault("source", source)
    _write_json(folder / "extraction.json", payload)
    return folder


def save_rejected_posting(
    posting_output: Path,
    posting: JobPosting,
    *,
    raw_html: str,
    extraction_data: dict[str, Any],
    rejection_reason: str,
    retrieval_method: str = "",
) -> Path:
    """Save artifacts for a posting rejected before ranking.

    Parameters:
        posting_output: Root output directory.
        posting: Extracted posting.
        raw_html: Downloaded page content.
        extraction_data: Extraction JSON payload.
        rejection_reason: Deterministic filter rejection reason.

    Returns:
        Path to the saved posting markdown file.
    """
    folder = _artifact_folder(posting_output, posting.company, posting.title)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "raw_download.html").write_text(raw_html, encoding="utf-8")
    payload = dict(extraction_data)
    payload["rejection_reason"] = rejection_reason
    _write_json(folder / "extraction.json", payload)
    if retrieval_method:
        _write_json(folder / "retrieval.json", {"retrieval_method": retrieval_method})
    markdown_path = folder / "posting.md"
    markdown_path.write_text(_format_posting_markdown(posting, rejection_reason=rejection_reason), encoding="utf-8")
    return markdown_path


def save_posting_markdown_with_artifacts(
    posting_output: Path,
    posting: JobPosting,
    *,
    raw_html: str,
    extraction_data: dict[str, Any],
    ranking_result: RankingResult,
) -> Path:
    """Backward-compatible helper that saves full success artifacts."""
    ranking_data = {
        "status": ranking_result.status.value,
        "overall": ranking_result.overall_score,
        "criterion_scores": ranking_result.criterion_scores,
        "reason": ranking_result.reason,
        "failure_reason": ranking_result.failure_reason,
    }
    return save_success_artifacts(
        posting_output,
        posting,
        raw_html=raw_html,
        extraction_data=extraction_data,
        ranking_data=ranking_data,
    )


def _artifact_folder(posting_output: Path, company: str, title: str) -> Path:
    return posting_output / sanitize_path_component(company) / sanitize_path_component(title, fallback="job_posting")


def _url_folder_name(url: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_")
    return slug[:120] or "unknown_url"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _format_posting_markdown(posting: JobPosting, *, rejection_reason: str = "") -> str:
    lines = [
        f"# {posting.title or 'Unknown Title'}",
        "",
        f"- **Company:** {posting.company}",
        f"- **Location:** {posting.location}",
        f"- **Extraction status:** {posting.extraction_status.value}",
    ]
    if posting.extraction_failure_reason:
        lines.append(f"- **Extraction failure reason:** {posting.extraction_failure_reason}")
    if rejection_reason:
        lines.append(f"- **Rejection reason:** {rejection_reason}")
    if posting.address:
        lines.append(f"- **Address:** {posting.address}")
    if posting.language:
        lines.append(f"- **Language:** {posting.language}")
    lines.append(f"- **URL:** {posting.url}")
    if posting.source:
        lines.append(f"- **Source:** {posting.source}")
    if posting.confidence_score is not None:
        lines.append(f"- **Confidence:** {posting.confidence_score:.2f}")
    elif posting.extraction_status.value == "FAILED":
        lines.append("- **Confidence:** N/A")
    lines.extend(["", "## Description", "", posting.description or "_No description extracted._"])
    return "\n".join(lines)
