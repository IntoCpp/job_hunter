"""Ranking tool for semantic job-posting evaluation."""

from __future__ import annotations

import logging

from job_hunter.models.config import AppConfig
from job_hunter.models.job_posting import JobPosting
from job_hunter.models.job_search_preferences import JobSearchPreferences
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.models.pipeline import RankingResult, StageStatus
from job_hunter.services.filtering_service import build_location_context, is_excluded_posting
from job_hunter.services.llm_service import LLMService
from job_hunter.services.preferences_service import format_preferences_for_prompt
from job_hunter.services.prompt_service import load_prompt

logger = logging.getLogger(__name__)


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

    def should_process(
        self,
        posting: JobPosting,
        profile: JobSearchProfile,
        preferences: JobSearchPreferences,
    ) -> tuple[bool, str]:
        """Apply deterministic filters before LLM ranking.

        Parameters:
            posting: Extracted posting.
            profile: Job search profile.
            preferences: User-maintained job search preferences.

        Returns:
            Tuple of (should_continue, rejection_reason).
        """
        if posting.extraction_status != StageStatus.SUCCESS or not posting.has_required_fields():
            return False, posting.extraction_failure_reason or "Extraction failed"
        if is_excluded_posting(posting, profile, preferences):
            return False, "Excluded by profile or user preference rules"
        if not self._location_is_acceptable(posting):
            return False, "Location outside acceptable areas"
        return True, ""

    def rank(
        self,
        posting: JobPosting,
        profile: JobSearchProfile,
        resume_context: str,
        preferences: JobSearchPreferences,
    ) -> RankingResult:
        """Compute semantic confidence score for a posting.

        Parameters:
            posting: Extracted posting.
            profile: Job search profile.
            resume_context: Combined resume input file contents.
            preferences: User-maintained job search preferences.

        Returns:
            Ranking result with overall and criterion scores.
        """
        if posting.extraction_status != StageStatus.SUCCESS or not posting.has_required_fields():
            reason = posting.extraction_failure_reason or "Missing required extraction fields"
            return RankingResult(
                status=StageStatus.FAILED,
                overall_score=None,
                reason="Ranking skipped",
                failure_reason=reason,
            )

        profile_summary = (
            f"Summary: {profile.summary}\n"
            f"Target titles: {', '.join(profile.target_titles)}\n"
            f"Equivalent titles: {', '.join(profile.equivalent_titles)}\n"
            f"Skills: {', '.join(profile.skills)}"
        )
        preferences_summary = format_preferences_for_prompt(preferences)
        posting_summary = (
            f"Language: {posting.language or 'unknown'}\n"
            f"Title: {posting.title}\n"
            f"Company: {posting.company}\n"
            f"Location: {posting.location}\n"
            f"Description: {posting.description[:4000]}"
        )
        data = self._llm.complete_json(
            model=self._config.models.ranking,
            system_prompt=load_prompt("rank_posting"),
            user_prompt=(
                f"AI PROFILE:\n{profile_summary}\n\n"
                f"USER PREFERENCES:\n{preferences_summary}\n\n"
                f"RESUME:\n{resume_context[:6000]}\n\n"
                f"POSTING:\n{posting_summary}"
            ),
        )
        overall = _score_value(data.get("overall", data.get("confidence", 0.0)))
        criterion_scores = {
            "software_relevance": _score_value(data.get("software_relevance", 0.0)),
            "leadership": _score_value(data.get("leadership", 0.0)),
            "management": _score_value(data.get("management", 0.0)),
            "location": _score_value(data.get("location", 0.0)),
        }
        reason = str(data.get("reason", ""))
        logger.info("Ranked %s at %.2f", posting.title, overall)
        return RankingResult(
            status=StageStatus.SUCCESS,
            overall_score=overall,
            criterion_scores=criterion_scores,
            reason=reason,
        )

    def _location_is_acceptable(self, posting: JobPosting) -> bool:
        if not self._config.locations:
            return True
        location_context = build_location_context(self._config.locations)
        data = self._llm.complete_json(
            model=self._config.models.location,
            system_prompt=load_prompt("location_filter"),
            user_prompt=(
                f"ACCEPTABLE LOCATIONS:\n{location_context}\n\n"
                f"POSTING LOCATION:\n{posting.location}\n"
                f"POSTING ADDRESS:\n{posting.address}"
            ),
        )
        return bool(data.get("acceptable", False))


def _score_value(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))
