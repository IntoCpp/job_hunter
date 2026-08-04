"""Command-line interface for Job-Hunter."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from job_hunter.agent.orchestrator import JobHunterAgent, RunOptions
from job_hunter.services.configuration_service import load_config, load_environment
from job_hunter.services.job_list_service import format_missing_job_postings_message, job_postings_file_exists
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
            "Process user-provided job posting URLs, rank them against a candidate profile, "
            "and optionally trigger resume customization."
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
        help="Enable test mode: limit to 2 new accepted postings and enable verbose logging",
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
    parser.add_argument(
        "--skip-resume",
        action="store_true",
        help="Run the full workflow but skip resume customization",
    )
    parser.add_argument(
        "--max",
        type=int,
        metavar="N",
        help="Stop after N new validated postings are added to accepted history",
    )
    parser.add_argument(
        "--url-postings",
        metavar="FILE_PATH",
        help="Override the configured job_postings_file path for this run",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Job-Hunter CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.test:
        args.verbose = True

    if args.max is not None and args.max < 1:
        parser.error("--max must be a positive integer")

    try:
        load_environment()
        config = load_config(Path(args.config))
        setup_logging(verbose=args.verbose, log_file=default_log_file(config.posting_output))
        agent = JobHunterAgent.from_config(config)

        if args.generate_job_search_profile:
            agent.generate_profile_only()
            return 0

        jobs_path = Path(args.url_postings).resolve() if args.url_postings else config.job_postings_file
        if not job_postings_file_exists(jobs_path):
            message = format_missing_job_postings_message(jobs_path)
            print(message, file=sys.stderr)
            logger.error(message)
            return 1

        job_postings_file = jobs_path if args.url_postings else None
        run_options = RunOptions(
            test_mode=args.test,
            skip_resume=args.skip_resume,
            max_new_postings=2 if args.test else args.max,
            job_postings_file=job_postings_file,
        )
        agent.run(options=run_options)
        return 0
    except Exception:
        logger.exception("Job-Hunter execution failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
