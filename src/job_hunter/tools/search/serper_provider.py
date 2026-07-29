"""Serper Google search provider."""

from __future__ import annotations

import logging

import httpx

from job_hunter.tools.search.base import SearchProvider, SearchResult

logger = logging.getLogger(__name__)

SERPER_SEARCH_URL = "https://google.serper.dev/search"


class SerperSearchProvider(SearchProvider):
    """Discover postings via Serper Google search API."""

    def __init__(self, api_key: str) -> None:
        """Initialize Serper provider.

        Parameters:
            api_key: Serper API key.
        """
        self._api_key = api_key

    def discover(self, queries: list[str]) -> list[SearchResult]:
        """Run Serper searches and collect organic result links.

        Parameters:
            queries: Search query strings.

        Returns:
            Unique search results.
        """
        results: list[SearchResult] = []
        seen: set[str] = set()
        with httpx.Client(timeout=30.0) as client:
            for query in queries:
                if not query.strip():
                    continue
                logger.debug("Serper query: %s", query)
                response = client.post(
                    SERPER_SEARCH_URL,
                    headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                    json={"q": query, "num": 10},
                )
                response.raise_for_status()
                payload = response.json()
                for item in payload.get("organic", []):
                    link = str(item.get("link", "")).strip()
                    if not link or link in seen:
                        continue
                    seen.add(link)
                    results.append(SearchResult(url=link, source="serper"))
        return results
