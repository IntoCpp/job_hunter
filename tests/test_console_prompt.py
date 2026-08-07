"""Tests for console prompt helpers."""

from unittest.mock import patch

from job_hunter.utils.console_prompt import prompt_browser_debug_ready


@patch("job_hunter.utils.console_prompt._wait_for_keypress")
def test_prompt_browser_debug_ready_shows_port(mock_wait: object, capsys) -> None:
    """Browser debug prompt includes the configured port."""
    prompt_browser_debug_ready(debug_port=9222)

    captured = capsys.readouterr()
    assert "msedge.exe --remote-debugging-port=9222" in captured.out
    assert "*** IMPORTANT: use port 9222 ***" in captured.out
    assert "Press any key to continue" in captured.out
