"""Console prompts for interactive CLI workflows."""

from __future__ import annotations

import sys


def prompt_browser_debug_ready(*, debug_port: int) -> None:
    """Prompt the user to confirm a debug-enabled browser is running.

    Parameters:
        debug_port: Remote debugging port Job-Hunter will connect to.
    """
    print(
        "Make sure you have started your browser for debug. Example:\n"
        f"  msedge.exe --remote-debugging-port={debug_port}\n"
        f"*** IMPORTANT: use port {debug_port} ***\n"
        "Press any key to continue...",
        file=sys.stdout,
    )
    _wait_for_keypress()


def _wait_for_keypress() -> None:
    if sys.platform == "win32":
        import msvcrt

        msvcrt.getch()
        print(file=sys.stdout)
        return
    input()
