"""Filename collision resolution for job posting output files."""

from __future__ import annotations

from pathlib import Path


def _suffix_for_index(index: int) -> str:
    """Convert a zero-based index to an alphabetical suffix (_a, _b, ..., _z, _aa, ...).

    Parameters:
        index: Zero-based suffix index.

    Returns:
        Suffix string without leading underscore (e.g. "a", "b", "aa").
    """
    if index < 0:
        raise ValueError("index must be non-negative")

    letters: list[str] = []
    value = index
    while True:
        letters.append(chr(ord("a") + (value % 26)))
        value = value // 26 - 1
        if value < 0:
            break
    return "".join(reversed(letters))


def resolve_collision_safe_path(directory: Path, base_name: str, extension: str = ".md") -> Path:
    """Return an available file path, appending alphabetical suffixes on collision.

    The original filename is preferred. Suffixes follow _a, _b, ..., _z, _aa, _ab, etc.

    Parameters:
        directory: Target directory for the file.
        base_name: Base filename without extension.
        extension: File extension including leading dot (default: ".md").

    Returns:
        Path that does not currently exist in directory.
    """
    if not extension.startswith("."):
        raise ValueError("extension must start with '.'")

    directory.mkdir(parents=True, exist_ok=True)

    candidate = directory / f"{base_name}{extension}"
    if not candidate.exists():
        return candidate

    index = 0
    while True:
        suffix = _suffix_for_index(index)
        candidate = directory / f"{base_name}_{suffix}{extension}"
        if not candidate.exists():
            return candidate
        index += 1
