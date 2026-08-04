"""Tests for user job posting list loading."""

from pathlib import Path

import pytest

from job_hunter.models.job_to_process import JobToProcess
from job_hunter.services.job_list_service import (
    format_missing_job_postings_message,
    job_postings_file_exists,
    load_job_postings,
)


def test_load_job_postings_reads_valid_file() -> None:
    """Valid job postings YAML loads company and URL pairs."""
    jobs = load_job_postings(Path("tests/test_data/sample_jobs_to_process.yaml"))

    assert jobs == [
        JobToProcess(company="Example Corp", url="https://example.com/jobs/1"),
        JobToProcess(company="Another Corp", url="https://example.com/jobs/2"),
    ]


def test_load_job_postings_missing_file(tmp_path: Path) -> None:
    """Missing job postings file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_job_postings(tmp_path / "missing.yaml")


def test_load_job_postings_requires_jobs_list(tmp_path: Path) -> None:
    """Job postings file must contain a jobs list."""
    path = tmp_path / "jobs.yaml"
    path.write_text("company: Example\n", encoding="utf-8")

    with pytest.raises(ValueError, match="jobs"):
        load_job_postings(path)


def test_format_missing_job_postings_message_includes_path() -> None:
    """Missing file message names the path and points to the sample file."""
    message = format_missing_job_postings_message(Path("config/missing_jobs.yaml"))

    assert "config/missing_jobs.yaml" in message
    assert "jobs_to_process.yaml.example" in message
    assert "--url-postings" in message


def test_job_postings_file_exists(tmp_path: Path) -> None:
    """Existence check reflects whether the file is on disk."""
    missing = tmp_path / "jobs.yaml"
    assert job_postings_file_exists(missing) is False

    missing.write_text("jobs: []\n", encoding="utf-8")
    assert job_postings_file_exists(missing) is True


def test_load_job_postings_requires_company_and_url(tmp_path: Path) -> None:
    """Each job entry requires company and url."""
    path = tmp_path / "jobs.yaml"
    path.write_text("jobs:\n  - company: Example Corp\n", encoding="utf-8")

    with pytest.raises(ValueError, match="requires a url"):
        load_job_postings(path)
