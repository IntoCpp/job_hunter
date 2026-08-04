"""Load and validate user job search preferences."""

from __future__ import annotations

from pathlib import Path

import yaml

from job_hunter.models.job_search_preferences import JobSearchPreferences, PreferredRole, RolePreference


def load_job_search_preferences(preferences_path: Path) -> JobSearchPreferences:
    """Load user job search preferences from YAML.

    Parameters:
        preferences_path: Path to ``my_job_preferences.yaml``.

    Returns:
        Parsed JobSearchPreferences instance.

    Raises:
        FileNotFoundError: If the preferences file does not exist.
        ValueError: If the file content is invalid.
    """
    if not preferences_path.exists():
        raise FileNotFoundError(f"Job search preferences file not found: {preferences_path}")

    with preferences_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"Job search preferences must be a YAML mapping: {preferences_path}")

    return JobSearchPreferences(
        preferred_roles=_parse_preferred_roles(data.get("preferred_roles", []), preferences_path),
        acceptable_roles=_parse_role_list(data.get("acceptable_roles", []), "acceptable_roles", preferences_path),
        excluded_roles=_parse_role_list(data.get("excluded_roles", []), "excluded_roles", preferences_path),
    )


def format_preferences_for_prompt(preferences: JobSearchPreferences) -> str:
    """Serialize user preferences for LLM ranking prompts.

    Parameters:
        preferences: User-maintained job search preferences.

    Returns:
        Human-readable preferences summary.
    """
    lines: list[str] = []
    if preferences.preferred_roles:
        lines.append("Preferred roles (lower priority number = higher preference):")
        for role in sorted(preferences.preferred_roles, key=lambda item: item.priority):
            detail = f" — {role.description}" if role.description else ""
            lines.append(f"- [{role.priority}] {role.title}{detail}")
    if preferences.acceptable_roles:
        lines.append("Acceptable roles:")
        for role in preferences.acceptable_roles:
            detail = f" — {role.description}" if role.description else ""
            lines.append(f"- {role.title}{detail}")
    if preferences.excluded_roles:
        lines.append("Excluded roles:")
        for role in preferences.excluded_roles:
            detail = f" — {role.description}" if role.description else ""
            lines.append(f"- {role.title}{detail}")
    return "\n".join(lines) if lines else "No explicit user preferences configured."


def _parse_preferred_roles(items: object, preferences_path: Path) -> list[PreferredRole]:
    if not isinstance(items, list):
        raise ValueError(f"preferred_roles must be a list in {preferences_path}")
    roles: list[PreferredRole] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"preferred_roles[{index}] must be a mapping in {preferences_path}")
        title = str(item.get("title", "")).strip()
        if not title:
            raise ValueError(f"preferred_roles[{index}].title is required in {preferences_path}")
        priority = item.get("priority", index + 1)
        try:
            priority_value = int(priority)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"preferred_roles[{index}].priority must be an integer in {preferences_path}") from exc
        roles.append(
            PreferredRole(
                title=title,
                priority=priority_value,
                description=str(item.get("description", "")).strip(),
            )
        )
    return roles


def _parse_role_list(items: object, field_name: str, preferences_path: Path) -> list[RolePreference]:
    if not isinstance(items, list):
        raise ValueError(f"{field_name} must be a list in {preferences_path}")
    roles: list[RolePreference] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{field_name}[{index}] must be a mapping in {preferences_path}")
        title = str(item.get("title", "")).strip()
        if not title:
            raise ValueError(f"{field_name}[{index}].title is required in {preferences_path}")
        roles.append(RolePreference(title=title, description=str(item.get("description", "")).strip()))
    return roles
