"""Tests for LLMService."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from job_hunter.services.llm_service import LLMService


@patch("job_hunter.services.llm_service.OpenAI")
def test_complete_text_uses_responses_api_with_store_true(mock_openai_cls: MagicMock) -> None:
    """Responses API calls must persist requests so they appear in OpenAI platform logs."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.responses.create.return_value = SimpleNamespace(output_text=" ranked ")

    service = LLMService(api_key="test-key")
    result = service.complete_text(
        model="gpt-4o-mini",
        system_prompt="You are helpful.",
        user_prompt="Rank this job.",
    )

    assert result == "ranked"
    mock_client.responses.create.assert_called_once_with(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Rank this job."},
        ],
        store=True,
    )
