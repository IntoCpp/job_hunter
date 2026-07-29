"""High-level search tool coordinating providers."""

from __future__ import annotations

import logging

from job_hunter.models.config import AppConfig
from job_hunter.models.job_search_preferences import JobSearchPreferences
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.services.preferences_service import build_search_titles
from job_hunter.tools.search.base import SearchResult
from job_hunter.tools.search.company_provider import CompanyWebsiteSearchProvider
from job_hunter.tools.search.job_board_provider import JobBoardSearchProvider
from job_hunter.tools.search.serper_provider import SerperSearchProvider

logger = logging.getLogger(__name__)


class SearchTool:
    """Coordinate search providers to discover job posting URLs."""

    def __init__(
        self,
        config: AppConfig,
        serper_provider: SerperSearchProvider,
        company_provider: CompanyWebsiteSearchProvider,
        job_board_provider: JobBoardSearchProvider,
    ) -> None:
        """Initialize search tool.

        Parameters:
            config: Application configuration.
            serper_provider: General Serper search provider.
            company_provider: Company website provider.
            job_board_provider: Job board provider.
        """
        self._config = config
        self._serper = serper_provider
        self._company = company_provider
        self._job_board = job_board_provider

    def discover_urls(self, profile: JobSearchProfile, preferences: JobSearchPreferences) -> list[str]:
        """Discover unique job posting URLs using all configured providers.

        Parameters:
            profile: Job search profile used to build queries.
            preferences: User-maintained job search preferences.

        Returns:
            Unique discovered URLs.
        """
        location_terms = [location.name for location in self._config.locations]
        search_titles = build_search_titles(profile.all_titles(), preferences)
        queries = self._build_general_queries(profile, location_terms, search_titles)
        logger.info("Searching job sources...")

        results: list[SearchResult] = []
        results.extend(self._serper.discover(queries))
        results.extend(self._job_board.discover_for_profile(profile, location_terms, search_titles))
        results.extend(self._company.discover_for_profile(profile, location_terms, search_titles))

        unique_urls: list[str] = []
        seen: set[str] = set()
        for item in results:
            if item.url in seen:
                continue
            seen.add(item.url)
            unique_urls.append(item.url)

        logger.info("Found %s posting URLs.", len(unique_urls))
        return unique_urls

    def _build_general_queries(
        self,
        profile: JobSearchProfile,
        location_terms: list[str],
        search_titles: list[str],
    ) -> list[str]:
        location_suffix = " ".join(location_terms[:2])
        queries: list[str] = []
        for title in search_titles[:5]:
            queries.append(f"\"{title}\" jobs {location_suffix}".strip())
        for keyword in profile.search_keywords[:3]:
            queries.append(f"{keyword} jobs {location_suffix}".strip())
        return queries
