"""Extraction tool for structured job posting data."""

from __future__ import annotations

import logging

from job_hunter.models.config import AppConfig
from job_hunter.models.job_posting import JobPosting, normalize_language
from job_hunter.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM_PROMPT = (
    "Extract structured job posting fields from HTML or text. "
    "Postings may be in English or French. Detect the primary language of the posting "
    "(use ISO 639-1 codes: en or fr). Preserve all extracted text fields in the original "
    "language of the posting; do not translate. "
    "Return JSON with keys: company, title, location, address, description, language."
)


class ExtractionTool:
    """Extract structured fields from downloaded posting content."""

    def __init__(self, config: AppConfig, llm_service: LLMService) -> None:
        """Initialize extraction tool.

        Parameters:
            config: Application configuration.
            llm_service: LLM service for extraction.
        """
        self._config = config
        self._llm = llm_service

    def extract(self, *, url: str, content: str) -> JobPosting:
        """Extract posting fields from raw page content.

        Parameters:
            url: Source URL.
            content: Downloaded page content.

        Returns:
            JobPosting with extracted fields.
        """
        logger.debug("Extracting posting data from %s", url)
        clipped = content[:12000]
        data = self._llm.complete_json(
            model=self._config.models.extraction,
            system_prompt=_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=f"URL: {url}\n\nCONTENT:\n{clipped}",
        )
        return JobPosting(
            title=str(data.get("title", "Unknown Title")),
            company=str(data.get("company", "Unknown Company")),
            location=str(data.get("location", "Unknown Location")),
            address=str(data.get("address", "")),
            description=str(data.get("description", "")),
            language=normalize_language(str(data.get("language", ""))),
            url=url,
            raw_content=content,
        )
