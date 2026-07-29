"""Filesystem path sanitization helpers."""

from __future__ import annotations

import re

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_path_component(value: str, fallback: str = "unknown") -> str:
    """Sanitize a string for use as a single filesystem path component.

    Parameters:
        value: Raw string (company name, job title, etc.).
        fallback: Value used when the sanitized result would be empty.

    Returns:
        Sanitized component with spaces replaced by underscores.
    """
    cleaned = _INVALID_CHARS.sub("", value.strip())
    cleaned = cleaned.replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    return cleaned or fallback
