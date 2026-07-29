"""Tests for resume tool invocation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from job_hunter.models.config import ResumeReworkConfig
from job_hunter.tools.resume_tool import ResumeTool, build_resume_command


def test_build_resume_command() -> None:
    """Resume command uses uv run with job posting path."""
    config = ResumeReworkConfig(
        script_path=Path("C:/tools/resume_rework.py"),
        working_directory=Path("C:/tools"),
    )
    posting = Path("tests/test_data/sample_job_posting.md")
    command = build_resume_command(config, posting)
    assert command[:3] == ["uv", "run", "resume_rework.py"]
    assert command[-2:] == ["--job-posting", str(posting.resolve())]


@patch("job_hunter.tools.resume_tool.subprocess.Popen")
def test_resume_tool_invoke_fire_and_forget(mock_popen: MagicMock, tmp_path: Path) -> None:
    """Resume tool starts subprocess without waiting."""
    posting = tmp_path / "job.md"
    posting.write_text("job", encoding="utf-8")
    config = ResumeReworkConfig(script_path=tmp_path / "resume_rework.py", working_directory=tmp_path)
    tool = ResumeTool(config)

    tool.invoke(posting)

    mock_popen.assert_called_once()
    kwargs = mock_popen.call_args.kwargs
    assert kwargs["cwd"] == tmp_path
