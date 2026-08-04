"""User-provided job posting input model."""

from __future__ import annotations

from dataclasses import dataclass

USER_INPUT_SOURCE = "user_input"


@dataclass(frozen=True)
class JobToProcess:
    """A job posting URL provided by the user for processing."""

    company: str
    url: str
