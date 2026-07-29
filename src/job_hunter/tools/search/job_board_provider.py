"""Job board site-restricted search provider."""

from __future__ import annotations

import logging

import httpx

from job_hunter.models.config import WebSitesConfig
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.tools.search.base import SearchProvider, SearchResult
from job_hunter.tools.search.page_links import extract_job_links_from_html, fetch_page_html
from job_hunter.tools.search.serper_provider import SerperSearchProvider

logger = logging.getLogger(__name__)


class JobBoardSearchProvider(SearchProvider):
    """Discover postings on configured job boards via site-restricted Serper queries and optional page URLs."""

    def __init__(
        self,
        serper: SerperSearchProvider,
        web_sites: WebSitesConfig,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Initialize job board provider.

        Parameters:
            serper: Serper provider used to execute searches.
            web_sites: Configured job boards.
            http_client: Optional shared HTTP client.
        """
        self._serper = serper
        self._web_sites = web_sites
        self._http_client = http_client

    def discover(self, queries: list[str]) -> list[SearchResult]:
        """Run site-restricted searches for each configured job board.

        Parameters:
            queries: Base search queries (unused; built from profile in search tool).

        Returns:
            Discovered search results tagged with job board source.
        """
        del queries
        return []

    def discover_for_profile(self, profile: JobSearchProfile, location_terms: list[str]) -> list[SearchResult]:
        """Build and run site-restricted queries from profile titles and locations.

        Parameters:
            profile: Job search profile.
            location_terms: Location names to include in queries.

        Returns:
            Discovered job board search results.
        """
        results: list[SearchResult] = []
        seen: set[str] = set()
        location_suffix = " ".join(location_terms[:2])

        for board in self._web_sites.job_boards:
            domain = board.resolved_domain()
            if not domain:
                logger.warning("Job board '%s' has no domain or url configured, skipping", board.name)
                continue

            if board.url.strip():
                html = fetch_page_html(board.url.strip(), self._http_client)
                if html:
                    for link in extract_job_links_from_html(board.url.strip(), html, domain):
                        if link not in seen:
                            seen.add(link)
                            results.append(SearchResult(url=link, source=f"job_board:{board.name}"))
                else:
                    logger.warning("Failed to fetch job board page %s", board.url)

            for title in profile.all_titles()[:5]:
                query = f'site:{domain} "{title}" {location_suffix}'.strip()
                for item in self._serper.discover([query]):
                    if item.url not in seen:
                        seen.add(item.url)
                        results.append(SearchResult(url=item.url, source=f"job_board:{board.name}"))

        return results
