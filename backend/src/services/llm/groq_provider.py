"""Groq LLM Provider.

Uses Groq's OpenAI-compatible API for fast inference of open-source models
(e.g., Llama 3, Mixtral). Ideal for simple generation tasks where speed matters.
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


DECOMMISSIONED_GROQ_MODELS = {
    "llama3-8b-8192": "openai/gpt-oss-20b",
    "llama3-70b-8192": "openai/gpt-oss-120b",
    "llama-3.1-8b-instant": "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
}


class GroqProvider(BaseLLMProvider):
    """Fast inference provider powered by Groq for open-source LLMs."""

    def __init__(self, model: str | None = None):
        raw_model = model or settings.groq_fast_model
        # Automatically map deprecated/decommissioned Groq model names to active equivalents
        self._model = DECOMMISSIONED_GROQ_MODELS.get(raw_model, raw_model)
        self._base_url = settings.groq_base_url
        self._api_key = settings.groq_api_key
        self._timeout = settings.llm_timeout

    @property
    def provider_name(self) -> str:
        return "groq"

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
        """Call Groq API with retry logic for transient failures."""
        if not self._api_key or self._api_key.startswith("your_") or "your_groq" in self._api_key:
            raise ValueError("GROQ_API_KEY is not configured")

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

        logger.info("Groq [%s] tokens used: %s", self._model, usage)
        return LLMResponse(
            content=content,
            model=self._model,
            provider="groq",
            usage=usage,
        )
