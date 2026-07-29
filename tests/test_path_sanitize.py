"""Tests for path sanitization."""

from job_hunter.utils.path_sanitize import sanitize_path_component


def test_sanitize_replaces_spaces_and_invalid_chars() -> None:
    """Invalid filesystem characters are removed or replaced."""
    assert sanitize_path_component("Software/Development: Manager") == "SoftwareDevelopment_Manager"


def test_sanitize_uses_fallback_for_empty_result() -> None:
    """Empty sanitized values fall back to a safe default."""
    assert sanitize_path_component("???") == "unknown"
