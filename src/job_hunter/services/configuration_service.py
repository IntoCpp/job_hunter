"""Configuration loading service."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from job_hunter.models.config import (
    AppConfig,
    BrowserSessionBrowserConfig,
    BrowserSessionConfig,
    JobSearchPreferencesConfig,
    LocationConfig,
    ModelConfig,
    ResumeReworkConfig,
    SearchProfileConfig,
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


def _parse_model_config(data: object, *, section_name: str) -> ModelConfig:
    if not isinstance(data, dict):
        raise ValueError(f"{section_name} must be a mapping")
    return ModelConfig(
        profile=str(data.get("profile", "gpt-4o-mini")),
        ranking=str(data.get("ranking", "gpt-4o")),
        location=str(data.get("location", "gpt-4o-mini")),
        extraction=str(data.get("extraction", "gpt-4o-mini")),
    )


def _parse_browser_session_config(data: object) -> BrowserSessionConfig:
    if not isinstance(data, dict):
        return BrowserSessionConfig()
    browsers: list[BrowserSessionBrowserConfig] = []
    for item in data.get("browsers", []):
        if not isinstance(item, dict):
            continue
        browser_type = str(item.get("type", "")).strip().casefold()
        if not browser_type:
            continue
        browsers.append(
            BrowserSessionBrowserConfig(
                type=browser_type,
                executable=str(item.get("executable", "")),
                user_data_dir=str(item.get("user_data_dir", "")),
            )
        )
    debug_port = data.get("debug_port", 9222)
    return BrowserSessionConfig(
        debug_host=str(data.get("debug_host", "127.0.0.1")),
        debug_port=int(debug_port),
        browsers=browsers,
    )


def load_config(config_path: Path, *, test_mode: bool = False) -> AppConfig:
    """Load application configuration from a YAML file.

    Parameters:
        config_path: Path to the YAML configuration file.
        test_mode: When True, use ``models_test``; otherwise use ``models_prod``.

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

    preferences_data = search_profile_data.get("job_search_preferences") or {}
    preferences_file = _resolve_path(str(preferences_data.get("file", "")), base_dir)
    if not preferences_file.name:
        raise ValueError("search_profile.job_search_preferences.file is required")
    if not preferences_file.exists():
        raise FileNotFoundError(f"Job search preferences file not found: {preferences_file}")

    if not str(data.get("job_postings_file", "")).strip():
        raise ValueError("job_postings_file is required")
    job_postings_file = _resolve_path(str(data.get("job_postings_file", "")), base_dir)

    resume_rework_data = data.get("resume_rework") or {}
    if "models_test" not in data:
        raise ValueError("models_test is required")
    if "models_prod" not in data:
        raise ValueError("models_prod is required")
    models_section = "models_test" if test_mode else "models_prod"
    models = _parse_model_config(data.get(models_section), section_name=models_section)

    return AppConfig(
        posting_output=_resolve_path(str(data.get("posting_output", "")), base_dir),
        posting_history=_resolve_path(str(data.get("posting_history", "")), base_dir),
        job_postings_file=job_postings_file,
        search_profile=SearchProfileConfig(
            input_files=input_files,
            output_file=output_file,
            job_search_preferences=JobSearchPreferencesConfig(file=preferences_file),
        ),
        resume_rework=ResumeReworkConfig(
            script_path=Path(str(resume_rework_data.get("script_path", ""))),
            working_directory=Path(str(resume_rework_data.get("working_directory", ""))),
        ),
        confidence_resume=float(data.get("confidence_resume", 0.9)),
        models=models,
        locations=[
            LocationConfig(name=str(item.get("name", "")), guidance=str(item.get("guidance", "")))
            for item in data.get("locations", [])
        ],
        browser_session=_parse_browser_session_config(data.get("browser_session")),
        config_path=config_path.resolve(),
    )
