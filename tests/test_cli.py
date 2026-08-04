"""Tests for the CLI argument parser and startup behavior."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from job_hunter.cli import build_parser, main


def test_parser_defaults() -> None:
    """Default config path and flags are set correctly."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.config == "config/config.yaml"
    assert args.test is False
    assert args.verbose is False
    assert args.generate_job_search_profile is False


def test_parser_generate_profile_flag() -> None:
    """Generate profile flag is accepted."""
    parser = build_parser()
    args = parser.parse_args(["--generate-job-search-profile", "--config", ".test/config.yaml"])
    assert args.generate_job_search_profile is True
    assert args.config == ".test/config.yaml"


def test_parser_skip_resume_and_max_flags() -> None:
    """Skip resume and max flags are accepted."""
    parser = build_parser()
    args = parser.parse_args(["--skip-resume", "--max", "5"])
    assert args.skip_resume is True
    assert args.max == 5


def test_parser_url_postings_flag() -> None:
    """URL postings override flag is accepted."""
    parser = build_parser()
    args = parser.parse_args(["--url-postings", "config/jobs_to_process.yaml"])
    assert args.url_postings == "config/jobs_to_process.yaml"


def test_parser_custom_config() -> None:
    """Custom config path is accepted."""
    parser = build_parser()
    args = parser.parse_args(["--config", ".test/config.yaml"])
    assert args.config == ".test/config.yaml"


@patch("job_hunter.cli.JobHunterAgent")
@patch("job_hunter.cli.setup_logging")
@patch("job_hunter.cli.load_config")
@patch("job_hunter.cli.load_environment")
def test_main_exits_gracefully_when_job_postings_file_missing(
    _load_environment: MagicMock,
    mock_load_config: MagicMock,
    _setup_logging: MagicMock,
    _agent_cls: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing job postings file prints guidance and exits without a traceback."""
    missing_jobs = tmp_path / "missing_jobs.yaml"
    config = MagicMock()
    config.posting_output = tmp_path / "output"
    config.job_postings_file = missing_jobs
    mock_load_config.return_value = config

    exit_code = main(["--config", str(tmp_path / "config.yaml")])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Job postings file not found" in captured.err
    assert missing_jobs.as_posix() in captured.err
    _agent_cls.from_config.return_value.run.assert_not_called()
