"""Load user-provided job posting lists from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from job_hunter.models.job_to_process import JobToProcess

_SAMPLE_FILE = Path("config/jobs_to_process.yaml.example")


def format_missing_job_postings_message(file_path: Path) -> str:
    """Build a user-friendly message when the job postings file is missing.

    Parameters:
        file_path: Configured or overridden job postings file path.

    Returns:
        Multi-line message suitable for console output.
    """
    return (
        f"Job postings file not found: {file_path.as_posix()}\n"
        "\n"
        "Create this file listing the jobs you want to process, or update "
        "`job_postings_file` in your config.\n"
        f"See {_SAMPLE_FILE.as_posix()} for the expected YAML format.\n"
        "\n"
        "You can also pass a different file with: --url-postings <FILE_PATH>"
    )


def job_postings_file_exists(file_path: Path) -> bool:
    """Return True when the job postings file exists on disk.

    Parameters:
        file_path: Path to the job postings YAML file.

    Returns:
        True if the file exists.
    """
    return file_path.exists()


def load_job_postings(file_path: Path) -> list[JobToProcess]:
    """Load job postings from a YAML file.

    Parameters:
        file_path: Path to the job postings YAML file.

    Returns:
        Parsed list of jobs to process.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file content is invalid.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Job postings file not found: {file_path}")

    with file_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Job postings file must be a YAML mapping: {file_path}")

    jobs_data = data.get("jobs")
    if not isinstance(jobs_data, list):
        raise ValueError(f"Job postings file must contain a 'jobs' list: {file_path}")
    if not jobs_data:
        raise ValueError(f"Job postings file must contain at least one job: {file_path}")

    jobs: list[JobToProcess] = []
    for index, item in enumerate(jobs_data, start=1):
        jobs.append(_parse_job_entry(item, file_path=file_path, index=index))
    return jobs


def _parse_job_entry(item: object, *, file_path: Path, index: int) -> JobToProcess:
    if not isinstance(item, dict):
        raise ValueError(f"Job entry #{index} in {file_path} must be a mapping")

    company = str(item.get("company", "")).strip()
    url = str(item.get("url", "")).strip()
    if not company:
        raise ValueError(f"Job entry #{index} in {file_path} requires a company")
    if not url:
        raise ValueError(f"Job entry #{index} in {file_path} requires a url")

    return JobToProcess(company=company, url=url)
