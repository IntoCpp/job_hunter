"""Search provider abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from job_hunter.utils.url import extract_domain

__all__ = ["SearchProvider", "SearchResult", "extract_domain"]


@dataclass(frozen=True)
class SearchResult:
    """Discovered job posting URL."""

    url: str
    source: str


class SearchProvider(ABC):
    """Interface for job posting URL discovery providers."""

    @abstractmethod
    def discover(self, queries: list[str]) -> list[SearchResult]:
        """Discover job posting URLs for the given queries.

        Parameters:
            queries: Search query strings.

        Returns:
            Discovered search results.
        """
