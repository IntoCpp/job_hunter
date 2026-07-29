"""Job posting domain model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class JobPosting:
    """Structured job posting discovered and processed by Job-Hunter."""

    title: str
    company: str
    location: str
    url: str
    description: str = ""
    address: str = ""
    confidence_score: float | None = None
    markdown_path: str = ""
    raw_content: str = field(default="", repr=False)
