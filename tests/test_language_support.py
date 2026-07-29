"""Tests for English/French language support."""

from pathlib import Path
from unittest.mock import MagicMock

from job_hunter.models.config import (
    AppConfig,
    JobSearchPreferencesConfig,
    ModelConfig,
    ResumeReworkConfig,
    SearchConfig,
    SearchProfileConfig,
    WebSitesConfig,
)
from job_hunter.models.job_posting import JobPosting, normalize_language
from job_hunter.services.history_service import HistoryService
from job_hunter.services.posting_writer import save_posting_markdown
from job_hunter.tools.extraction_tool import ExtractionTool


def test_normalize_language_accepts_supported_codes() -> None:
    """Language normalization maps common values to ISO 639-1 codes."""
    assert normalize_language("en") == "en"
    assert normalize_language("English") == "en"
    assert normalize_language("fr") == "fr"
    assert normalize_language("Français") == "fr"
    assert normalize_language("unknown") == ""


def test_extraction_tool_preserves_language(tmp_path: Path) -> None:
    """Extraction stores detected language without translating content."""
    config = AppConfig(
        posting_output=tmp_path,
        posting_history=tmp_path / "history.yaml",
        search_profile=SearchProfileConfig(
            input_files=[],
            output_file=tmp_path / "profile.yaml",
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
    llm = MagicMock()
    llm.complete_json.return_value = {
        "company": "Hydro-Québec",
        "title": "Directeur de développement logiciel",
        "location": "Montréal",
        "address": "",
        "description": "Responsable de la livraison des projets logiciels.",
        "language": "fr",
    }
    tool = ExtractionTool(config, llm)

    posting = tool.extract(url="https://example.com/job", content="<html>offre</html>")

    assert posting.language == "fr"
    assert posting.title == "Directeur de développement logiciel"
    assert "livraison" in posting.description


def test_save_posting_markdown_includes_language_metadata(tmp_path: Path) -> None:
    """Saved markdown records posting language and preserves French content."""
    posting = JobPosting(
        title="Directeur de développement logiciel",
        company="Example Corp",
        location="Montréal",
        url="https://example.com/job/1",
        description="Responsable de la livraison des projets logiciels.",
        language="fr",
        confidence_score=0.88,
    )

    saved = save_posting_markdown(posting, tmp_path)
    content = saved.read_text(encoding="utf-8")

    assert "- **Language:** fr" in content
    assert "Directeur de développement logiciel" in content
    assert "Responsable de la livraison" in content


def test_history_service_records_language_metadata(tmp_path: Path) -> None:
    """History metadata stores detected posting language."""
    history_path = tmp_path / "history.yaml"
    service = HistoryService(history_path)
    posting = JobPosting(
        title="Software Manager",
        company="Example Corp",
        location="Montreal",
        url="https://example.com/job/1",
        language="en",
        confidence_score=0.9,
    )

    service.add_entry(posting, markdown_path=str(tmp_path / "posting.md"))
    service.save()

    reloaded = HistoryService(history_path)
    assert reloaded._entries[0].metadata["language"] == "en"
