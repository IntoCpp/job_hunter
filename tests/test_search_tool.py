"""Tests for search tool query building."""

from unittest.mock import MagicMock

from job_hunter.models.config import (
    AppConfig,
    LocationConfig,
    ModelConfig,
    ResumeReworkConfig,
    SearchConfig,
    SearchProfileConfig,
    WebSitesConfig,
)
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.tools.search.company_provider import CompanyWebsiteSearchProvider
from job_hunter.tools.search.job_board_provider import JobBoardSearchProvider
from job_hunter.tools.search.search_tool import SearchTool
from job_hunter.tools.search.serper_provider import SerperSearchProvider


def _config() -> AppConfig:
    return AppConfig(
        posting_output=MagicMock(),
        posting_history=MagicMock(),
        search_profile=SearchProfileConfig(input_files=[], output_file=MagicMock()),
        resume_rework=ResumeReworkConfig(script_path=MagicMock(), working_directory=MagicMock()),
        confidence_resume=0.9,
        models=ModelConfig("a", "b", "c", "d", "e"),
        locations=[LocationConfig(name="Montreal Greater Area", guidance="Montreal region")],
        web_sites=WebSitesConfig(),
        search=SearchConfig(provider="serper"),
        config_path=MagicMock(),
    )


def test_search_tool_deduplicates_urls() -> None:
    """Search tool returns unique URLs across providers."""
    config = _config()
    serper = MagicMock()
    serper.discover.return_value = [
        MagicMock(url="https://example.com/1", source="serper"),
        MagicMock(url="https://example.com/1", source="serper"),
        MagicMock(url="https://example.com/2", source="serper"),
    ]
    company = MagicMock(spec=CompanyWebsiteSearchProvider)
    company.discover_for_profile.return_value = []
    board = MagicMock(spec=JobBoardSearchProvider)
    board.discover_for_profile.return_value = []

    tool = SearchTool(config, serper, company, board)
    profile = JobSearchProfile(target_titles=["Engineering Manager"], search_keywords=["python"])

    urls = tool.discover_urls(profile)

    assert urls == ["https://example.com/1", "https://example.com/2"]
