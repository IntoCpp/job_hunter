"""Ranking tool for semantic job-posting evaluation."""

from __future__ import annotations

import logging

from job_hunter.models.config import AppConfig
from job_hunter.models.job_posting import JobPosting
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.services.filtering_service import build_location_context, is_excluded_posting
from job_hunter.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_LOCATION_SYSTEM_PROMPT = (
    "Decide if a job posting location matches any acceptable configured locations. "
    "Location text may be in English or French. "
    "Return JSON with keys: acceptable (boolean), reason (string)."
)

_RANKING_SYSTEM_PROMPT = (
    "Score how well a job posting matches the candidate profile on a 0.00 to 1.00 scale. "
    "The posting may be in English or French; evaluate fit regardless of language. "
    "Interpret equivalent job titles and responsibilities across languages "
    "(for example, 'Directeur de développement logiciel' and 'Software Development Manager'). "
    "Return JSON with keys: confidence (number), reason (string)."
)


class RankingTool:
    """Apply deterministic filters and LLM-based semantic ranking."""

    def __init__(self, config: AppConfig, llm_service: LLMService) -> None:
        """Initialize ranking tool.

        Parameters:
            config: Application configuration.
            llm_service: LLM service for location and ranking evaluation.
        """
        self._config = config
        self._llm = llm_service

    def should_process(self, posting: JobPosting, profile: JobSearchProfile) -> tuple[bool, str]:
        """Apply deterministic filters before LLM ranking.

        Parameters:
            posting: Extracted posting.
            profile: Job search profile.

        Returns:
            Tuple of (should_continue, rejection_reason).
        """
        if is_excluded_posting(posting, profile):
            return False, "Excluded by profile rules"
        if not self._location_is_acceptable(posting):
            return False, "Location outside acceptable areas"
        return True, ""

    def rank(self, posting: JobPosting, profile: JobSearchProfile, resume_context: str) -> float:
        """Compute semantic confidence score for a posting.

        Parameters:
            posting: Extracted posting.
            profile: Job search profile.
            resume_context: Combined resume input file contents.

        Returns:
            Confidence score between 0.00 and 1.00.
        """
        profile_summary = (
            f"Summary: {profile.summary}\n"
            f"Target titles: {', '.join(profile.target_titles)}\n"
            f"Equivalent titles: {', '.join(profile.equivalent_titles)}\n"
            f"Skills: {', '.join(profile.skills)}"
        )
        posting_summary = (
            f"Language: {posting.language or 'unknown'}\n"
            f"Title: {posting.title}\n"
            f"Company: {posting.company}\n"
            f"Location: {posting.location}\n"
            f"Description: {posting.description[:4000]}"
        )
        data = self._llm.complete_json(
            model=self._config.models.ranking,
            system_prompt=_RANKING_SYSTEM_PROMPT,
            user_prompt=f"PROFILE:\n{profile_summary}\n\nRESUME:\n{resume_context[:6000]}\n\nPOSTING:\n{posting_summary}",
        )
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        logger.info("Ranked %s at %.2f", posting.title, confidence)
        return confidence

    def _location_is_acceptable(self, posting: JobPosting) -> bool:
        if not self._config.locations:
            return True
        location_context = build_location_context(self._config.locations)
        data = self._llm.complete_json(
            model=self._config.models.location,
            system_prompt=_LOCATION_SYSTEM_PROMPT,
            user_prompt=(
                f"ACCEPTABLE LOCATIONS:\n{location_context}\n\n"
                f"POSTING LOCATION:\n{posting.location}\n"
                f"POSTING ADDRESS:\n{posting.address}"
            ),
        )
        return bool(data.get("acceptable", False))
