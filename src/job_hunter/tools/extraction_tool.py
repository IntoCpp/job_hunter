"""Extraction tool for structured job posting data."""

from __future__ import annotations

import logging
from typing import Any

from job_hunter.models.config import AppConfig
from job_hunter.models.job_posting import (
    UNKNOWN_LOCATION,
    UNKNOWN_TITLE,
    JobPosting,
    is_present_field,
    normalize_language,
)
from job_hunter.models.job_to_process import USER_INPUT_SOURCE
from job_hunter.models.pipeline import StageStatus
from job_hunter.services.llm_service import LLMService
from job_hunter.services.prompt_service import load_prompt

logger = logging.getLogger(__name__)


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

    def extract(
        self,
        *,
        url: str,
        content: str,
        user_company: str,
        source: str = USER_INPUT_SOURCE,
    ) -> tuple[JobPosting, dict[str, Any]]:
        """Extract posting fields from raw page content.

        Parameters:
            url: Source URL.
            content: Downloaded page content.
            user_company: Authoritative company name from the user job list.
            source: History source identifier.

        Returns:
            Tuple of extracted posting and extraction JSON payload.
        """
        logger.debug("Extracting posting data from %s", url)
        clipped = content[:12000]
        raw_data = self._llm.complete_json(
            model=self._config.models.extraction,
            system_prompt=load_prompt("extract_posting"),
            user_prompt=f"URL: {url}\n\nCONTENT:\n{clipped}",
        )
        extracted_company = _clean_field(raw_data.get("company"))
        posting = JobPosting(
            title=_clean_field(raw_data.get("title"), fallback=UNKNOWN_TITLE),
            company=user_company.strip(),
            location=_clean_field(raw_data.get("location"), fallback=UNKNOWN_LOCATION),
            address=_clean_field(raw_data.get("address")),
            description=_clean_field(raw_data.get("description")),
            language=normalize_language(str(raw_data.get("language", ""))),
            url=url,
            raw_content=content,
            source=source,
            extracted_company=extracted_company,
        )
        extraction_payload = _build_extraction_payload(posting, raw_data)
        posting, extraction_payload = self._apply_validation(posting, extraction_payload)
        return posting, extraction_payload

    def _apply_validation(
        self,
        posting: JobPosting,
        extraction_payload: dict[str, Any],
    ) -> tuple[JobPosting, dict[str, Any]]:
        if posting.has_required_fields():
            posting.extraction_status = StageStatus.SUCCESS
            posting.extraction_failure_reason = ""
            extraction_payload["extraction_status"] = StageStatus.SUCCESS.value
            extraction_payload["failure_reason"] = ""
            return posting, extraction_payload

        missing_fields = [
            name
            for name, value in (
                ("company", posting.company),
                ("title", posting.title),
                ("description", posting.description),
            )
            if not is_present_field(value)
        ]
        reason = f"Missing required fields: {', '.join(missing_fields)}"
        posting.extraction_status = StageStatus.FAILED
        posting.extraction_failure_reason = reason
        extraction_payload["extraction_status"] = StageStatus.FAILED.value
        extraction_payload["failure_reason"] = reason
        logger.warning("Extraction failed for %s: %s", posting.url, reason)
        return posting, extraction_payload


def _clean_field(value: object, *, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not is_present_field(text):
        return fallback
    return text


def _build_extraction_payload(posting: JobPosting, raw_data: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "company": posting.company,
        "title": posting.title,
        "location": posting.location,
        "address": posting.address,
        "description": posting.description,
        "language": posting.language,
        "url": posting.url,
        "source": posting.source,
        "raw_model_output": raw_data,
        "extraction_status": posting.extraction_status.value,
        "failure_reason": posting.extraction_failure_reason,
    }
    if posting.extracted_company:
        payload["extracted_company"] = posting.extracted_company
    return payload
