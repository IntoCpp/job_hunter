"""JobHunter Agent orchestration."""

from __future__ import annotations

import logging
from pathlib import Path

from job_hunter.models.config import AppConfig
from job_hunter.services.configuration_service import get_required_env
from job_hunter.services.history_service import HistoryService
from job_hunter.services.llm_service import LLMService
from job_hunter.services.posting_writer import save_posting_markdown
from job_hunter.services.preferences_service import load_job_search_preferences
from job_hunter.services.profile_service import ProfileService, read_input_files
from job_hunter.tools.download_tool import DownloadTool
from job_hunter.tools.extraction_tool import ExtractionTool
from job_hunter.tools.ranking_tool import RankingTool
from job_hunter.tools.resume_tool import ResumeTool
from job_hunter.tools.search.company_provider import CompanyWebsiteSearchProvider
from job_hunter.tools.search.job_board_provider import JobBoardSearchProvider
from job_hunter.tools.search.search_tool import SearchTool
from job_hunter.tools.search.serper_provider import SerperSearchProvider

logger = logging.getLogger(__name__)


class JobHunterAgent:
    """Coordinate Job-Hunter workflow execution."""

    def __init__(
        self,
        config: AppConfig,
        *,
        profile_service: ProfileService,
        history_service: HistoryService,
        search_tool: SearchTool,
        download_tool: DownloadTool,
        extraction_tool: ExtractionTool,
        ranking_tool: RankingTool,
        resume_tool: ResumeTool,
    ) -> None:
        """Initialize orchestrator with tool dependencies."""
        self._config = config
        self._profile_service = profile_service
        self._history = history_service
        self._search = search_tool
        self._download = download_tool
        self._extract = extraction_tool
        self._rank = ranking_tool
        self._resume = resume_tool

    @classmethod
    def from_config(cls, config: AppConfig) -> "JobHunterAgent":
        """Build agent and dependencies from application configuration.

        Parameters:
            config: Loaded application configuration.

        Returns:
            Configured JobHunterAgent instance.
        """
        openai_key = get_required_env("OPENAI_API_KEY")
        serper_key = get_required_env("SERPER_API_KEY")
        llm = LLMService(api_key=openai_key)
        serper = SerperSearchProvider(api_key=serper_key)
        return cls(
            config,
            profile_service=ProfileService(config, llm),
            history_service=HistoryService(config.posting_history),
            search_tool=SearchTool(
                config,
                serper,
                CompanyWebsiteSearchProvider(serper, config.web_sites),
                JobBoardSearchProvider(serper, config.web_sites),
            ),
            download_tool=DownloadTool(),
            extraction_tool=ExtractionTool(config, llm),
            ranking_tool=RankingTool(config, llm),
            resume_tool=ResumeTool(config.resume_rework),
        )

    def generate_profile_only(self) -> Path:
        """Regenerate job search profile and exit workflow.

        Returns:
            Path to saved profile file.
        """
        logger.info("Generating job search profile...")
        profile = self._profile_service.generate()
        self._profile_service.save(profile)
        logger.info("Job search profile saved to %s", self._profile_service.output_file)
        return self._profile_service.output_file

    def run(self, *, test_mode: bool = False) -> None:
        """Execute the full Job-Hunter workflow.

        Parameters:
            test_mode: When True, process at most two postings.
        """
        logger.info("Loading configuration...")
        profile = self._profile_service.load_or_generate()
        logger.info("Loading job search profile...")
        preferences = load_job_search_preferences(self._config.search_profile.job_search_preferences.file)
        logger.info("Loading job search preferences...")
        resume_context = read_input_files(self._config.search_profile.input_files)

        urls = self._search.discover_urls(profile, preferences)
        processed = 0
        posting_limit = 2 if test_mode else None

        for url in urls:
            if posting_limit is not None and processed >= posting_limit:
                break
            try:
                if self._process_url(url, profile, preferences, resume_context):
                    processed += 1
            except Exception:
                logger.exception("Failed to process posting URL: %s", url)

        self._history.save()
        logger.info("Completed. Processed %s new postings.", processed)

    def _process_url(self, url: str, profile, preferences, resume_context: str) -> bool:
        logger.debug("Downloading %s", url)
        content = self._download.download(url)
        posting = self._extract.extract(url=url, content=content)

        if self._history.is_duplicate(posting):
            self._history.touch_duplicate(posting)
            return False

        should_process, reason = self._rank.should_process(posting, profile, preferences)
        if not should_process:
            logger.info("Skipping %s: %s", posting.title, reason)
            return False

        posting.confidence_score = self._rank.rank(posting, profile, resume_context, preferences)
        markdown_path = save_posting_markdown(posting, self._config.posting_output)
        posting.markdown_path = str(markdown_path)
        self._history.add_entry(posting, markdown_path=str(markdown_path))

        if posting.confidence_score >= self._config.confidence_resume:
            self._resume.invoke(markdown_path)

        logger.info("Saved posting to %s", markdown_path)
        return True
