"""OpenAI LLM Provider.

Uses the OpenAI API for reasoning-heavy tasks (GPT-4o, GPT-4o-mini).
Routes complex analysis requests that benefit from deep reasoning.
"""

import logging
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from src.services.llm.base import BaseLLMProvider, LLMResponse
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OpenAIProvider(BaseLLMProvider):
    """Reasoning-focused provider using OpenAI models."""

    def __init__(self):
        self._model = settings.openai_reasoning_model
        self._base_url = settings.openai_base_url
        self._api_key = settings.openai_api_key
        self._timeout = settings.llm_timeout

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Call OpenAI API with retry logic."""
        if not self._api_key or self._api_key.startswith("your_") or "your_openai" in self._api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        logger.info("OpenAI [%s] tokens used: %s", self._model, usage)
        return LLMResponse(
            content=content,
            model=self._model,
            provider="openai",
            usage=usage,
        )
