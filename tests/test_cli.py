"""Tests for the CLI argument parser."""

from job_hunter.cli import build_parser


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
