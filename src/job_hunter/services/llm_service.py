"""LLM interaction service."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMService:
    """Thin wrapper around the OpenAI Responses API for structured tasks."""

    def __init__(self, api_key: str) -> None:
        """Initialize the LLM service.

        Parameters:
            api_key: OpenAI API key.
        """
        self._client = OpenAI(api_key=api_key)

    def complete_text(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        """Request a plain-text completion from the model.

        Parameters:
            model: OpenAI model identifier.
            system_prompt: System instructions.
            user_prompt: User content.

        Returns:
            Model response text.
        """
        response = self._client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            store=True,
            # temperature=0.2, # In comment: Got an exception: With the selected model (gpt-5.6-sol), only the default value '1' is allowed.
        )
        content = response.output_text or ""
        logger.debug("LLM response length: %s", len(content))
        return content.strip()

    def complete_json(self, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Request a JSON object from the model.

        Parameters:
            model: OpenAI model identifier.
            system_prompt: System instructions.
            user_prompt: User content.

        Returns:
            Parsed JSON object.

        Raises:
            ValueError: If the response is not valid JSON.
        """
        text = self.complete_text(model=model, system_prompt=system_prompt, user_prompt=user_prompt)
        cleaned = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Model did not return valid JSON: {text[:200]}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Model JSON response must be an object")
        return parsed
