"""Tests for job board search provider."""

from unittest.mock import MagicMock, patch

from job_hunter.models.config import JobBoard, WebSitesConfig
from job_hunter.models.job_search_profile import JobSearchProfile
from job_hunter.tools.search.job_board_provider import JobBoardSearchProvider
from job_hunter.tools.search.serper_provider import SerperSearchProvider


def test_job_board_provider_uses_configured_domain() -> None:
    """Site-restricted queries use domain from YAML configuration."""
    serper = MagicMock(spec=SerperSearchProvider)
    serper.discover.return_value = []
    web_sites = WebSitesConfig(job_boards=[JobBoard(name="LinkedIn", domain="linkedin.com")])
    provider = JobBoardSearchProvider(serper, web_sites)
    profile = JobSearchProfile(target_titles=["Engineering Manager"])

    provider.discover_for_profile(profile, ["Montreal"])

    serper.discover.assert_called()
    query = serper.discover.call_args[0][0][0]
    assert "site:linkedin.com" in query


@patch("job_hunter.tools.search.job_board_provider.fetch_page_html")
def test_job_board_provider_fetches_configured_url(mock_fetch: MagicMock) -> None:
    """When url is configured, the provider fetches that page for job links."""
    mock_fetch.return_value = '<a href="https://emploi.hydroquebec.com/job/123">job posting</a>'
    serper = MagicMock(spec=SerperSearchProvider)
    serper.discover.return_value = []
    board = JobBoard(
        name="Hydro-Québec IT",
        url="https://emploi.hydroquebec.com/go/Technologies-information-et-communications/2661617/",
    )
    provider = JobBoardSearchProvider(serper, WebSitesConfig(job_boards=[board]))
    profile = JobSearchProfile(target_titles=["Engineer"])

    results = provider.discover_for_profile(profile, ["Montreal"])

    mock_fetch.assert_called_once_with(board.url, None)
    assert any("emploi.hydroquebec.com" in item.url for item in results)
