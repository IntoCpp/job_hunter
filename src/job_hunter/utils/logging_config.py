"""Logging configuration for Job-Hunter."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(*, verbose: bool, log_file: Path | None = None) -> None:
    """Configure application logging for console and optional file output.

    Parameters:
        verbose: When True, use DEBUG level; otherwise INFO.
        log_file: Optional path for per-execution log file.
    """
    level = logging.DEBUG if verbose else logging.INFO
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def default_log_file(posting_output: Path) -> Path:
    """Build the default per-execution log file path.

    Parameters:
        posting_output: Configured posting output directory.

    Returns:
        Path under posting_output/logs/ with a timestamped filename.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return posting_output / "logs" / f"{timestamp}.log"
