"""Persist job postings as Markdown files."""

from __future__ import annotations

from pathlib import Path

from job_hunter.models.job_posting import JobPosting
from job_hunter.services.filename_service import resolve_collision_safe_path
from job_hunter.utils.path_sanitize import sanitize_path_component


def save_posting_markdown(posting: JobPosting, posting_output: Path) -> Path:
    """Save a job posting as Markdown under posting_output/company/title.md.

    Parameters:
        posting: Posting to save.
        posting_output: Configured output directory.

    Returns:
        Path to the saved Markdown file.
    """
    company_dir = posting_output / sanitize_path_component(posting.company)
    base_name = sanitize_path_component(posting.title, fallback="job_posting")
    target = resolve_collision_safe_path(company_dir, base_name)
    content = _format_markdown(posting)
    target.write_text(content, encoding="utf-8")
    return target


def _format_markdown(posting: JobPosting) -> str:
    lines = [
        f"# {posting.title}",
        "",
        f"- **Company:** {posting.company}",
        f"- **Location:** {posting.location}",
    ]
    if posting.address:
        lines.append(f"- **Address:** {posting.address}")
    lines.append(f"- **URL:** {posting.url}")
    if posting.confidence_score is not None:
        lines.append(f"- **Confidence:** {posting.confidence_score:.2f}")
    lines.extend(["", "## Description", "", posting.description or "_No description extracted._"])
    return "\n".join(lines)
