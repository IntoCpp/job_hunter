"""Tests for extraction validation."""

from pathlib import Path
from unittest.mock import MagicMock

from job_hunter.models.config import (
    AppConfig,
    JobSearchPreferencesConfig,
    ModelConfig,
    ResumeReworkConfig,
    SearchProfileConfig,
)
from job_hunter.models.pipeline import StageStatus
from job_hunter.tools.extraction_tool import ExtractionTool
from job_hunter.tools.ranking_tool import RankingTool


def _config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        posting_output=tmp_path,
        posting_history=tmp_path / "history.yaml",
        job_postings_file=tmp_path / "jobs.yaml",
        search_profile=SearchProfileConfig(
            input_files=[],
            output_file=tmp_path / "profile.yaml",
            job_search_preferences=JobSearchPreferencesConfig(file=tmp_path / "preferences.yaml"),
        ),
        resume_rework=ResumeReworkConfig(script_path=tmp_path / "script.py", working_directory=tmp_path),
        confidence_resume=0.9,
        models=ModelConfig("profile", "ranking", "location", "extraction"),
        locations=[],
        config_path=tmp_path / "config.yaml",
    )


def test_extraction_marks_missing_required_fields_as_failed(tmp_path: Path) -> None:
    """Extraction fails when title or description are missing while preserving user company."""
    llm = MagicMock()
    llm.complete_json.return_value = {
        "company": None,
        "title": "Software Development Manager",
        "location": "Montreal",
        "address": "",
        "description": None,
        "language": "en",
    }
    tool = ExtractionTool(_config(tmp_path), llm)

    posting, payload = tool.extract(
        url="https://example.com/job",
        content="<html>job</html>" * 50,
        user_company="Example Corp",
    )

    assert posting.extraction_status == StageStatus.FAILED
    assert posting.company == "Example Corp"
    assert "description" in posting.extraction_failure_reason
    assert payload["extraction_status"] == StageStatus.FAILED.value


def test_extraction_stores_extracted_company_metadata(tmp_path: Path) -> None:
    """Extracted company is stored separately when it differs from user input."""
    llm = MagicMock()
    llm.complete_json.return_value = {
        "company": "Example Corp Inc.",
        "title": "Software Development Manager",
        "location": "Montreal",
        "address": "",
        "description": "Lead software teams with responsibilities and qualifications.",
        "language": "en",
    }
    tool = ExtractionTool(_config(tmp_path), llm)

    posting, payload = tool.extract(
        url="https://example.com/job",
        content="<html>job</html>" * 50,
        user_company="Example Corporation",
    )

    assert posting.company == "Example Corporation"
    assert posting.extracted_company == "Example Corp Inc."
    assert payload["extracted_company"] == "Example Corp Inc."


def test_ranking_refuses_incomplete_posting(tmp_path: Path) -> None:
    """Ranking returns N/A when extraction did not succeed."""
    from job_hunter.models.job_posting import JobPosting
    from job_hunter.models.job_search_preferences import JobSearchPreferences
    from job_hunter.models.job_search_profile import JobSearchProfile

    posting = JobPosting(
        title="Software Development Manager",
        company="Example Corp",
        location="Montreal",
        url="https://example.com/job",
        description="",
        extraction_status=StageStatus.FAILED,
        extraction_failure_reason="Missing required fields: description",
    )
    rank = RankingTool(_config(tmp_path), MagicMock())

    result = rank.rank(posting, JobSearchProfile(), "resume", JobSearchPreferences())

    assert result.status == StageStatus.FAILED
    assert result.overall_score is None
    assert "description" in result.failure_reason.lower()
