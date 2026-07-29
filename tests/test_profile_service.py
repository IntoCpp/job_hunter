"""Tests for profile service cache behavior."""

from pathlib import Path
from unittest.mock import MagicMock

import yaml

from job_hunter.models.config import (
    AppConfig,
    JobSearchPreferencesConfig,
    ModelConfig,
    ResumeReworkConfig,
    SearchConfig,
    SearchProfileConfig,
    WebSitesConfig,
)
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.services.profile_service import ProfileService


def _config(tmp_path: Path) -> AppConfig:
    input_file = tmp_path / "resume.md"
    input_file.write_text("# Resume", encoding="utf-8")
    output_file = tmp_path / "job_search_profile.yaml"
    return AppConfig(
        posting_output=tmp_path / "output",
        posting_history=tmp_path / "history.yaml",
        search_profile=SearchProfileConfig(
            input_files=[input_file],
            output_file=output_file,
            job_search_preferences=JobSearchPreferencesConfig(file=tmp_path / "preferences.yaml"),
        ),
        resume_rework=ResumeReworkConfig(script_path=tmp_path / "script.py", working_directory=tmp_path),
        confidence_resume=0.9,
        models=ModelConfig("a", "b", "c", "d", "e"),
        locations=[],
        web_sites=WebSitesConfig(),
        search=SearchConfig(provider="serper"),
        config_path=tmp_path / "config.yaml",
    )


def test_profile_load_or_generate_uses_cache(tmp_path: Path) -> None:
    """Existing cache is loaded without calling the LLM."""
    config = _config(tmp_path)
    cached = {
        "target_titles": ["Engineering Manager"],
        "equivalent_titles": [],
        "job_descriptions": [],
        "skills": ["Python"],
        "seniority_level": "manager",
        "preferred_industries": [],
        "excluded_titles": [],
        "excluded_companies": [],
        "search_keywords": [],
        "summary": "Test profile",
    }
    config.search_profile.output_file.write_text(yaml.safe_dump(cached), encoding="utf-8")
    llm = MagicMock()
    service = ProfileService(config, llm)

    profile = service.load_or_generate()

    assert profile.target_titles == ["Engineering Manager"]
    llm.complete_text.assert_not_called()


def test_profile_generate_writes_cache(tmp_path: Path) -> None:
    """Missing cache triggers generation and save."""
    config = _config(tmp_path)
    llm = MagicMock()
    llm.complete_text.return_value = yaml.safe_dump(
        {
            "target_titles": ["Team Lead"],
            "equivalent_titles": [],
            "job_descriptions": [],
            "skills": [],
            "seniority_level": "",
            "preferred_industries": [],
            "excluded_titles": [],
            "excluded_companies": [],
            "search_keywords": [],
            "summary": "",
        }
    )
    service = ProfileService(config, llm)

    profile = service.load_or_generate()

    assert isinstance(profile, JobSearchProfile)
    assert config.search_profile.output_file.exists()
