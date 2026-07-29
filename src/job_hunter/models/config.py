"""Configuration data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from job_hunter.utils.url import extract_domain


@dataclass
class SearchProfileConfig:
    """Inputs and output path for job search profile generation."""

    input_files: list[Path]
    output_file: Path


@dataclass
class ResumeReworkConfig:
    """External resume customization script settings."""

    script_path: Path
    working_directory: Path


@dataclass
class ModelConfig:
    """OpenAI model identifiers for AI-assisted operations."""

    agent: str
    profile: str
    ranking: str
    location: str
    extraction: str


@dataclass
class LocationConfig:
    """Human-readable location definition for matching."""

    name: str
    description: str


@dataclass
class CompanySite:
    """Company career page URL (site root or sub-page)."""

    url: str


@dataclass
class JobBoard:
    """Job board search source defined in configuration."""

    name: str
    domain: str = ""
    url: str = ""

    def resolved_domain(self) -> str:
        """Return the search domain for site-restricted queries.

        Returns:
            Explicit domain if set, otherwise domain derived from url.
        """
        if self.domain.strip():
            return self.domain.strip().lower().removeprefix("www.")
        if self.url.strip():
            return extract_domain(self.url)
        return ""


@dataclass
class WebSitesConfig:
    """Configured search sources."""

    companies: list[CompanySite] = field(default_factory=list)
    job_boards: list[JobBoard] = field(default_factory=list)


@dataclass
class SearchConfig:
    """Search provider configuration."""

    provider: str


@dataclass
class AppConfig:
    """Top-level application configuration loaded from YAML."""

    posting_output: Path
    posting_history: Path
    search_profile: SearchProfileConfig
    resume_rework: ResumeReworkConfig
    confidence_resume: float
    models: ModelConfig
    locations: list[LocationConfig]
    web_sites: WebSitesConfig
    search: SearchConfig
    config_path: Path
