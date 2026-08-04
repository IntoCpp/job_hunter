"""JobHunter Agent orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from job_hunter.models.config import AppConfig
from job_hunter.models.job_to_process import USER_INPUT_SOURCE, JobToProcess
from job_hunter.models.pipeline import StageStatus
from job_hunter.services.artifact_service import (
    save_failed_download_artifacts,
    save_failed_extraction_artifacts,
    save_rejected_posting,
    save_success_artifacts,
)
from job_hunter.services.configuration_service import get_required_env
from job_hunter.services.history_service import HistoryService
from job_hunter.services.job_list_service import format_missing_job_postings_message, job_postings_file_exists, load_job_postings
from job_hunter.services.llm_service import LLMService
from job_hunter.services.page_validation_service import validate_downloaded_page
from job_hunter.services.preferences_service import load_job_search_preferences
from job_hunter.services.profile_service import ProfileService, read_input_files
from job_hunter.tools.download_tool import DownloadTool
from job_hunter.tools.extraction_tool import ExtractionTool
from job_hunter.tools.ranking_tool import RankingTool
from job_hunter.tools.resume_tool import ResumeTool

logger = logging.getLogger(__name__)


class ProcessOutcome(str, Enum):
    """Outcome of processing a single posting URL."""

    NEW_ACCEPTED = "new_accepted"
    DUPLICATE = "duplicate"
    FAILED_OR_SKIPPED = "failed_or_skipped"


@dataclass
class RunOptions:
    """Runtime options for a workflow execution."""

    test_mode: bool = False
    skip_resume: bool = False
    max_new_postings: int | None = None
    job_postings_file: Path | None = None


class JobHunterAgent:
    """Coordinate Job-Hunter workflow execution."""

    def __init__(
        self,
        config: AppConfig,
        *,
        profile_service: ProfileService,
        history_service: HistoryService,
        download_tool: DownloadTool,
        extraction_tool: ExtractionTool,
        ranking_tool: RankingTool,
        resume_tool: ResumeTool,
    ) -> None:
        """Initialize orchestrator with tool dependencies."""
        self._config = config
        self._profile_service = profile_service
        self._history = history_service
        self._download = download_tool
        self._extract = extraction_tool
        self._rank = ranking_tool
        self._resume = resume_tool

    @classmethod
    def from_config(cls, config: AppConfig) -> "JobHunterAgent":
        """Build agent and dependencies from application configuration."""
        openai_key = get_required_env("OPENAI_API_KEY")
        llm = LLMService(api_key=openai_key)
        return cls(
            config,
            profile_service=ProfileService(config, llm),
            history_service=HistoryService(config.posting_history),
            download_tool=DownloadTool(),
            extraction_tool=ExtractionTool(config, llm),
            ranking_tool=RankingTool(config, llm),
            resume_tool=ResumeTool(config.resume_rework),
        )

    def generate_profile_only(self) -> Path:
        """Regenerate job search profile and exit workflow."""
        logger.info("Generating job search profile...")
        profile = self._profile_service.generate()
        self._profile_service.save(profile)
        logger.info("Job search profile saved to %s", self._profile_service.output_file)
        return self._profile_service.output_file

    def run(self, *, options: RunOptions | None = None) -> None:
        """Execute the full Job-Hunter workflow."""
        run_options = options or RunOptions()
        logger.info("Loading configuration...")
        profile = self._profile_service.load_or_generate()
        logger.info("Loading job search profile...")
        preferences = load_job_search_preferences(self._config.search_profile.job_search_preferences.file)
        logger.info("Loading job search preferences...")
        resume_context = read_input_files(self._config.search_profile.input_files)

        jobs_path = run_options.job_postings_file or self._config.job_postings_file
        if not job_postings_file_exists(jobs_path):
            message = format_missing_job_postings_message(jobs_path)
            logger.error(message)
            return

        logger.info("Loading job postings from %s", jobs_path)
        jobs = load_job_postings(jobs_path)

        new_accepted = 0
        posting_limit = 2 if run_options.test_mode else run_options.max_new_postings

        for job in jobs:
            if posting_limit is not None and new_accepted >= posting_limit:
                break
            try:
                outcome = self._process_job(job, profile, preferences, resume_context, run_options)
                if outcome == ProcessOutcome.NEW_ACCEPTED:
                    new_accepted += 1
            except Exception:
                logger.exception("Failed to process posting URL: %s", job.url)

        self._history.save()
        logger.info("Completed. Added %s new accepted postings.", new_accepted)

    def _process_job(
        self,
        job: JobToProcess,
        profile,
        preferences,
        resume_context: str,
        options: RunOptions,
    ) -> ProcessOutcome:
        url = job.url
        source = USER_INPUT_SOURCE
        logger.debug("Downloading %s", url)
        try:
            content = self._download.download(url)
        except RuntimeError as exc:
            reason = str(exc)
            self._history.add_failed_download(
                url=url,
                failure_reason=reason,
                source=source,
                page_type="download_error",
            )
            save_failed_download_artifacts(
                self._config.posting_output,
                url=url,
                raw_html="",
                failure_reason=reason,
                page_type="download_error",
                source=source,
            )
            return ProcessOutcome.FAILED_OR_SKIPPED

        download_validation = validate_downloaded_page(content)
        if download_validation.status != StageStatus.SUCCESS:
            self._history.add_failed_download(
                url=url,
                failure_reason=download_validation.failure_reason,
                source=source,
                page_type=download_validation.page_type.value,
            )
            save_failed_download_artifacts(
                self._config.posting_output,
                url=url,
                raw_html=content,
                failure_reason=download_validation.failure_reason,
                page_type=download_validation.page_type.value,
                source=source,
            )
            logger.info("Skipping %s: %s", url, download_validation.failure_reason)
            return ProcessOutcome.FAILED_OR_SKIPPED

        posting, extraction_payload = self._extract.extract(
            url=url,
            content=content,
            user_company=job.company,
            source=source,
        )
        if posting.extraction_status != StageStatus.SUCCESS:
            artifact_path = save_failed_extraction_artifacts(
                self._config.posting_output,
                url=url,
                raw_html=content,
                extraction_data=extraction_payload,
                source=source,
            )
            self._history.add_failed_extraction(
                posting,
                failure_reason=posting.extraction_failure_reason,
                artifact_path=str(artifact_path),
            )
            logger.info("Skipping %s: %s", url, posting.extraction_failure_reason)
            return ProcessOutcome.FAILED_OR_SKIPPED

        if self._history.is_duplicate(posting):
            self._history.touch_duplicate(posting)
            return ProcessOutcome.DUPLICATE

        should_process, reason = self._rank.should_process(posting, profile, preferences)
        if not should_process:
            markdown_path = save_rejected_posting(
                self._config.posting_output,
                posting,
                raw_html=content,
                extraction_data=extraction_payload,
                rejection_reason=reason,
            )
            self._history.add_rejected(
                posting,
                markdown_path=str(markdown_path),
                rejection_reason=reason,
            )
            logger.info("Skipping %s: %s", posting.title, reason)
            return ProcessOutcome.FAILED_OR_SKIPPED

        ranking_result = self._rank.rank(posting, profile, resume_context, preferences)
        if ranking_result.status != StageStatus.SUCCESS or ranking_result.overall_score is None:
            logger.info("Skipping ranking for %s: %s", posting.title, ranking_result.failure_reason)
            return ProcessOutcome.FAILED_OR_SKIPPED

        posting.confidence_score = ranking_result.overall_score
        ranking_payload = {
            "status": ranking_result.status.value,
            "overall": ranking_result.overall_score,
            "criterion_scores": ranking_result.criterion_scores,
            "reason": ranking_result.reason,
            "failure_reason": ranking_result.failure_reason,
        }
        markdown_path = save_success_artifacts(
            self._config.posting_output,
            posting,
            raw_html=content,
            extraction_data=extraction_payload,
            ranking_data=ranking_payload,
        )
        posting.markdown_path = str(markdown_path)
        self._history.add_entry(posting, markdown_path=str(markdown_path), ranking_result=ranking_result)

        if not options.skip_resume and posting.confidence_score >= self._config.confidence_resume:
            self._resume.invoke(markdown_path)

        logger.info("Saved posting to %s", markdown_path)
        return ProcessOutcome.NEW_ACCEPTED
