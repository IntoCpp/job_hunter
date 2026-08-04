"""Configuration data models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class JobSearchPreferencesConfig:
    """Path to the user-maintained job search preferences file."""

    file: Path


@dataclass
class SearchProfileConfig:
    """Inputs and output path for job search profile generation."""

    input_files: list[Path]
    output_file: Path
    job_search_preferences: JobSearchPreferencesConfig


@dataclass
class ResumeReworkConfig:
    """External resume customization script settings."""

    script_path: Path
    working_directory: Path


@dataclass
class ModelConfig:
    """OpenAI model identifiers for AI-assisted operations."""

    profile: str
    ranking: str
    location: str
    extraction: str


@dataclass
class LocationConfig:
    """Human-readable location definition for AI-assisted matching."""

    name: str
    guidance: str


@dataclass
class AppConfig:
    """Top-level application configuration loaded from YAML."""

    posting_output: Path
    posting_history: Path
    job_postings_file: Path
    search_profile: SearchProfileConfig
    resume_rework: ResumeReworkConfig
    confidence_resume: float
    models: ModelConfig
    locations: list[LocationConfig]
    config_path: Path
