"""Command-line interface for Job-Hunter."""

from __future__ import annotations

import argparse
import sys


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

    # Phase 3 will implement orchestration; setup validates CLI wiring only.
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
