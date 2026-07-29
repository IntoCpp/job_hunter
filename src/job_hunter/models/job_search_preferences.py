"""User-maintained job search preferences model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PreferredRole:
    """A role the user wants to prioritize during search and ranking."""

    title: str
    priority: int = 0
    description: str = ""


@dataclass
class RolePreference:
    """A role the user considers acceptable or excluded."""

    title: str
    description: str = ""


@dataclass
class JobSearchPreferences:
    """Explicit user preferences that guide job discovery and ranking."""

    preferred_roles: list[PreferredRole] = field(default_factory=list)
    acceptable_roles: list[RolePreference] = field(default_factory=list)
    excluded_roles: list[RolePreference] = field(default_factory=list)

    def search_titles(self) -> list[str]:
        """Return unique role titles for search queries, preferred roles first.

        Returns:
            Deduplicated titles from preferred and acceptable roles.
        """
        seen: set[str] = set()
        titles: list[str] = []
        preferred = sorted(self.preferred_roles, key=lambda role: role.priority)
        for role in [*preferred, *self.acceptable_roles]:
            normalized = role.title.strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            titles.append(normalized)
        return titles

    def excluded_titles(self) -> list[str]:
        """Return excluded role titles from user preferences."""
        return [role.title.strip() for role in self.excluded_roles if role.title.strip()]
