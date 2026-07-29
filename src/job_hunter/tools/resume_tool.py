"""Resume customization script invocation."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from job_hunter.models.config import ResumeReworkConfig

logger = logging.getLogger(__name__)


class ResumeTool:
    """Invoke the external resume customization script."""

    def __init__(self, config: ResumeReworkConfig) -> None:
        """Initialize resume tool.

        Parameters:
            config: Resume rework script configuration.
        """
        self._config = config

    def invoke(self, job_posting_path: Path) -> subprocess.Popen[bytes]:
        """Start resume rework for a saved posting (fire-and-forget).

        Parameters:
            job_posting_path: Path to saved Markdown posting.

        Returns:
            Started subprocess handle.
        """
        command = [
            "uv",
            "run",
            self._config.script_path.name,
            "--job-posting",
            str(job_posting_path.resolve()),
        ]
        logger.info("Starting resume rework for %s", job_posting_path)
        return subprocess.Popen(
            command,
            cwd=self._config.working_directory,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def build_resume_command(config: ResumeReworkConfig, job_posting_path: Path) -> list[str]:
    """Build resume rework command for testing.

    Parameters:
        config: Resume rework configuration.
        job_posting_path: Saved posting path.

    Returns:
        Command argv list.
    """
    return [
        "uv",
        "run",
        str(config.script_path.name),
        "--job-posting",
        str(job_posting_path.resolve()),
    ]
