"""Configuration loading service."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from job_hunter.models.config import (
    AppConfig,
    CompanySite,
    JobBoard,
    LocationConfig,
    ModelConfig,
    ResumeReworkConfig,
    SearchConfig,
    SearchProfileConfig,
    WebSitesConfig,
)


def load_environment() -> None:
    """Load environment variables from a .env file when present."""
    load_dotenv()


def get_required_env(name: str) -> str:
    """Return a required environment variable.

    Parameters:
        name: Environment variable name.

    Returns:
        Variable value.

    Raises:
        ValueError: If the variable is missing or empty.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _parse_job_board(item: object) -> JobBoard:
    if not isinstance(item, dict):
        raise ValueError("Each job_board entry must be a mapping")
    name = str(item.get("name", "")).strip()
    domain = str(item.get("domain", "")).strip()
    url = str(item.get("url", "")).strip()
    if not name:
        raise ValueError("Each job_board entry requires a name")
    if not domain and not url:
        raise ValueError(f"Job board '{name}' requires domain or url")
    return JobBoard(name=name, domain=domain, url=url)


def load_config(config_path: Path) -> AppConfig:
    """Load application configuration from a YAML file.

    Parameters:
        config_path: Path to the YAML configuration file.

    Returns:
        Parsed AppConfig instance.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If required fields are missing or invalid.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    base_dir = config_path.parent.resolve()
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    search_profile_data = data.get("search_profile") or {}
    input_files = [
        _resolve_path(str(path), base_dir)
        for path in search_profile_data.get("input_files", [])
    ]
    output_file = _resolve_path(str(search_profile_data.get("output_file", "")), base_dir)
    if not input_files or not output_file.name:
        raise ValueError("search_profile.input_files and search_profile.output_file are required")

    resume_rework_data = data.get("resume_rework") or {}
    models_data = data.get("models") or {}
    web_sites_data = data.get("web_sites") or {}

    return AppConfig(
        posting_output=_resolve_path(str(data.get("posting_output", "")), base_dir),
        posting_history=_resolve_path(str(data.get("posting_history", "")), base_dir),
        search_profile=SearchProfileConfig(input_files=input_files, output_file=output_file),
        resume_rework=ResumeReworkConfig(
            script_path=Path(str(resume_rework_data.get("script_path", ""))),
            working_directory=Path(str(resume_rework_data.get("working_directory", ""))),
        ),
        confidence_resume=float(data.get("confidence_resume", 0.9)),
        models=ModelConfig(
            agent=str(models_data.get("agent", "gpt-4o-mini")),
            profile=str(models_data.get("profile", "gpt-4o-mini")),
            ranking=str(models_data.get("ranking", "gpt-4o")),
            location=str(models_data.get("location", "gpt-4o-mini")),
            extraction=str(models_data.get("extraction", "gpt-4o-mini")),
        ),
        locations=[
            LocationConfig(name=str(item.get("name", "")), description=str(item.get("description", "")))
            for item in data.get("locations", [])
        ],
        web_sites=WebSitesConfig(
            companies=[CompanySite(url=str(item.get("url", ""))) for item in web_sites_data.get("companies", [])],
            job_boards=[_parse_job_board(item) for item in web_sites_data.get("job_boards", [])],
        ),
        search=SearchConfig(provider=str((data.get("search") or {}).get("provider", "serper"))),
        config_path=config_path.resolve(),
    )
