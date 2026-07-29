"""Company career site search provider."""

from __future__ import annotations

import logging

import httpx

from job_hunter.models.config import WebSitesConfig
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.tools.search.base import SearchProvider, SearchResult
from job_hunter.tools.search.page_links import extract_job_links_from_html, fetch_page_html
from job_hunter.tools.search.serper_provider import SerperSearchProvider
from job_hunter.utils.url import extract_domain

logger = logging.getLogger(__name__)


class CompanyWebsiteSearchProvider(SearchProvider):
    """Discover postings from company career pages via HTTP link extraction and Serper."""

    def __init__(
        self,
        serper: SerperSearchProvider,
        web_sites: WebSitesConfig,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Initialize company website provider.

        Parameters:
            serper: Serper provider for site-restricted fallback search.
            web_sites: Configured company career URLs.
            http_client: Optional shared HTTP client.
        """
        self._serper = serper
        self._web_sites = web_sites
        self._http_client = http_client

    def discover(self, queries: list[str]) -> list[SearchResult]:
        """Discover URLs using configured company pages.

        Parameters:
            queries: Unused at provider level.

        Returns:
            Empty list; use discover_for_profile instead.
        """
        del queries
        return []

    def discover_for_profile(self, profile: JobSearchProfile, location_terms: list[str]) -> list[SearchResult]:
        """Discover job links from company sites and Serper site queries.

        Parameters:
            profile: Job search profile.
            location_terms: Location names for Serper queries.

        Returns:
            Discovered company-site search results.
        """
        results: list[SearchResult] = []
        seen: set[str] = set()
        location_suffix = " ".join(location_terms[:2])

        for company in self._web_sites.companies:
            domain = extract_domain(company.url)
            if not domain:
                continue

            page_links = self._extract_links_from_page(company.url, domain)
            for link in page_links:
                if link not in seen:
                    seen.add(link)
                    results.append(SearchResult(url=link, source=f"company:{domain}"))

            for title in profile.all_titles()[:3]:
                query = f"site:{domain} \"{title}\" {location_suffix}".strip()
                for item in self._serper.discover([query]):
                    if item.url not in seen:
                        seen.add(item.url)
                        results.append(SearchResult(url=item.url, source=f"company:{domain}"))

        return results

    def _extract_links_from_page(self, page_url: str, domain: str) -> list[str]:
        html = fetch_page_html(page_url, self._http_client)
        if not html:
            logger.warning("Failed to fetch company page %s", page_url)
            return []
        return extract_job_links_from_html(page_url, html, domain)
