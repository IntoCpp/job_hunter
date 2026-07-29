"""Tests for filename collision resolution."""

from pathlib import Path

import pytest

from job_hunter.services.filename_service import _suffix_for_index, resolve_collision_safe_path


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (0, "a"),
        (1, "b"),
        (25, "z"),
        (26, "aa"),
        (27, "ab"),
        (51, "az"),
        (52, "ba"),
    ],
)
def test_suffix_for_index(index: int, expected: str) -> None:
    """Alphabetical suffix sequence matches the design specification."""
    assert _suffix_for_index(index) == expected


def test_suffix_for_index_rejects_negative() -> None:
    """Negative indices are rejected."""
    with pytest.raises(ValueError, match="non-negative"):
        _suffix_for_index(-1)


def test_resolve_prefers_original_filename(tmp_path: Path) -> None:
    """Original filename is used when no collision exists."""
    result = resolve_collision_safe_path(tmp_path, "Software_Development_Manager")
    assert result == tmp_path / "Software_Development_Manager.md"
    assert not result.exists()


def test_resolve_appends_suffix_on_collision(tmp_path: Path) -> None:
    """Suffixes are appended when the base filename already exists."""
    base = tmp_path / "Software_Development_Manager.md"
    base.write_text("original", encoding="utf-8")

    result = resolve_collision_safe_path(tmp_path, "Software_Development_Manager")
    assert result == tmp_path / "Software_Development_Manager_a.md"


def test_resolve_sequential_collisions(tmp_path: Path) -> None:
    """Multiple collisions resolve to successive alphabetical suffixes."""
    (tmp_path / "Role.md").write_text("1", encoding="utf-8")
    (tmp_path / "Role_a.md").write_text("2", encoding="utf-8")
    (tmp_path / "Role_b.md").write_text("3", encoding="utf-8")

    result = resolve_collision_safe_path(tmp_path, "Role")
    assert result == tmp_path / "Role_c.md"


def test_resolve_z_then_aa(tmp_path: Path) -> None:
    """After _z, the next suffix is _aa."""
    (tmp_path / "Role.md").write_text("base", encoding="utf-8")
    for index in range(26):
        suffix = _suffix_for_index(index)
        (tmp_path / f"Role_{suffix}.md").write_text(suffix, encoding="utf-8")

    result = resolve_collision_safe_path(tmp_path, "Role")
    assert result == tmp_path / "Role_aa.md"


def test_resolve_rejects_extension_without_dot() -> None:
    """Extension must include a leading dot."""
    with pytest.raises(ValueError, match="extension"):
        resolve_collision_safe_path(Path("."), "name", extension="md")
