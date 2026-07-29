"""Job search profile model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class JobDescriptionEntry:
    """Role description entry in a job search profile."""

    title: str
    description: str


@dataclass
class JobSearchProfile:
    """AI-generated search criteria consumed by search and ranking tools."""

    target_titles: list[str] = field(default_factory=list)
    equivalent_titles: list[str] = field(default_factory=list)
    job_descriptions: list[JobDescriptionEntry] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    seniority_level: str = ""
    preferred_industries: list[str] = field(default_factory=list)
    excluded_titles: list[str] = field(default_factory=list)
    excluded_companies: list[str] = field(default_factory=list)
    search_keywords: list[str] = field(default_factory=list)
    summary: str = ""

    def all_titles(self) -> list[str]:
        """Return unique target and equivalent titles for search queries."""
        seen: set[str] = set()
        titles: list[str] = []
        for title in [*self.target_titles, *self.equivalent_titles]:
            normalized = title.strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            titles.append(normalized)
        return titles
