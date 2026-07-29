"""Job search profile generation and loading."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from job_hunter.models.config import AppConfig
from job_hunter.models.job_search_profile import JobDescriptionEntry, JobSearchProfile
from job_hunter.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_PROFILE_SYSTEM_PROMPT = (
    "You analyze candidate materials and produce structured job search criteria as YAML. "
    "The candidate may search in a bilingual English/French job market (for example, Montreal). "
    "Include both English and French titles and keywords where appropriate in target_titles, "
    "equivalent_titles, and search_keywords. "
    "Return only valid YAML with these keys: target_titles, equivalent_titles, job_descriptions, "
    "skills, seniority_level, preferred_industries, excluded_titles, excluded_companies, "
    "search_keywords, summary. job_descriptions must be a list of objects with title and description."
)


class ProfileService:
    """Generate, load, and persist the job search profile cache."""

    def __init__(self, config: AppConfig, llm_service: LLMService) -> None:
        """Initialize the profile service.

        Parameters:
            config: Application configuration.
            llm_service: LLM service used for profile generation.
        """
        self._config = config
        self._llm = llm_service

    @property
    def output_file(self) -> Path:
        """Return configured profile cache path."""
        return self._config.search_profile.output_file

    def load_or_generate(self, *, force_regenerate: bool = False) -> JobSearchProfile:
        """Load cached profile or generate it when missing.

        Parameters:
            force_regenerate: When True, always regenerate and overwrite cache.

        Returns:
            Loaded or newly generated job search profile.
        """
        if force_regenerate or not self.output_file.exists():
            profile = self.generate()
            self.save(profile)
            return profile
        return self.load()

    def load(self) -> JobSearchProfile:
        """Load profile from the cache file.

        Returns:
            Parsed JobSearchProfile.

        Raises:
            FileNotFoundError: If the cache file does not exist.
        """
        if not self.output_file.exists():
            raise FileNotFoundError(f"Job search profile not found: {self.output_file}")
        with self.output_file.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return _profile_from_dict(data)

    def save(self, profile: JobSearchProfile) -> None:
        """Write profile to the configured cache file.

        Parameters:
            profile: Profile to persist.
        """
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "target_titles": profile.target_titles,
            "equivalent_titles": profile.equivalent_titles,
            "job_descriptions": [
                {"title": item.title, "description": item.description} for item in profile.job_descriptions
            ],
            "skills": profile.skills,
            "seniority_level": profile.seniority_level,
            "preferred_industries": profile.preferred_industries,
            "excluded_titles": profile.excluded_titles,
            "excluded_companies": profile.excluded_companies,
            "search_keywords": profile.search_keywords,
            "summary": profile.summary,
        }
        with self.output_file.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
        logger.info("Job search profile saved to %s", self.output_file)

    def generate(self) -> JobSearchProfile:
        """Generate a profile from configured input files using the LLM.

        Returns:
            Generated job search profile.
        """
        logger.info("Generating job search profile...")
        combined_input = read_input_files(self._config.search_profile.input_files)
        yaml_text = self._llm.complete_text(
            model=self._config.models.profile,
            system_prompt=_PROFILE_SYSTEM_PROMPT,
            user_prompt=combined_input,
        )
        cleaned = yaml_text.removeprefix("```yaml").removeprefix("```").removesuffix("```").strip()
        data = yaml.safe_load(cleaned) or {}
        return _profile_from_dict(data)


def read_input_files(paths: list[Path]) -> str:
    """Read and combine configured profile input files.

    Parameters:
        paths: Input file paths.

    Returns:
        Combined text with file headers.
    """
    sections: list[str] = []
    for path in paths:
        if not path.exists():
            logger.warning("Input file not found, skipping: %s", path)
            continue
        content = path.read_text(encoding="utf-8")
        sections.append(f"### FILE: {path.name}\n{content}")
    return "\n\n".join(sections)


def _profile_from_dict(data: dict) -> JobSearchProfile:
    descriptions = [
        JobDescriptionEntry(title=str(item.get("title", "")), description=str(item.get("description", "")))
        for item in data.get("job_descriptions", [])
        if isinstance(item, dict)
    ]
    return JobSearchProfile(
        target_titles=[str(v) for v in data.get("target_titles", [])],
        equivalent_titles=[str(v) for v in data.get("equivalent_titles", [])],
        job_descriptions=descriptions,
        skills=[str(v) for v in data.get("skills", [])],
        seniority_level=str(data.get("seniority_level", "")),
        preferred_industries=[str(v) for v in data.get("preferred_industries", [])],
        excluded_titles=[str(v) for v in data.get("excluded_titles", [])],
        excluded_companies=[str(v) for v in data.get("excluded_companies", [])],
        search_keywords=[str(v) for v in data.get("search_keywords", [])],
        summary=str(data.get("summary", "")),
    )
