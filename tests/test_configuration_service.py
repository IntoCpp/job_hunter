"""Tests for configuration loading."""

from pathlib import Path

import pytest

from job_hunter.services.configuration_service import load_config


def test_load_test_config() -> None:
    """Test configuration file loads with expected sections."""
    config = load_config(Path(".test/config.yaml"))
    assert config.confidence_resume == 0.90
    assert config.search.provider == "serper"
    assert len(config.search_profile.input_files) == 2
    assert config.search_profile.output_file.name == "job_search_profile.yaml"


def test_load_config_missing_file(tmp_path: Path) -> None:
    """Missing configuration file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.yaml")


def test_load_config_job_board_requires_domain_or_url(tmp_path: Path) -> None:
    """Job board entries must include domain or url."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
posting_output: "out"
posting_history: "history.yaml"
search_profile:
  input_files: ["resume.md"]
  output_file: "profile.yaml"
resume_rework:
  script_path: "script.py"
  working_directory: "."
web_sites:
  job_boards:
    - name: "Broken"
""",
        encoding="utf-8",
    )
    (tmp_path / "resume.md").write_text("resume", encoding="utf-8")

    with pytest.raises(ValueError, match="requires domain or url"):
        load_config(config_file)
