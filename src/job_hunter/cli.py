"""Command-line interface for Job-Hunter."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from job_hunter.agent.orchestrator import JobHunterAgent
from job_hunter.services.configuration_service import load_config, load_environment
from job_hunter.utils.logging_config import default_log_file, setup_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for Job-Hunter.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="job-hunter",
        description=(
            "Search the Internet for job postings that match a candidate profile, "
            "rank them, and optionally trigger resume customization."
        ),
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to the YAML configuration file (default: config/config.yaml)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Enable test mode: limit to 2 postings and enable verbose logging",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging (automatically enabled when --test is used)",
    )
    parser.add_argument(
        "--generate-job-search-profile",
        action="store_true",
        help="Generate or regenerate the job search profile only, then exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Job-Hunter CLI.

    Parameters:
        argv: Optional argument list (defaults to sys.argv[1:]).

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.test:
        args.verbose = True

    try:
        load_environment()
        config = load_config(Path(args.config))
        setup_logging(verbose=args.verbose, log_file=default_log_file(config.posting_output))
        agent = JobHunterAgent.from_config(config)

        if args.generate_job_search_profile:
            agent.generate_profile_only()
            return 0

        agent.run(test_mode=args.test)
        return 0
    except Exception:
        logger.exception("Job-Hunter execution failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
