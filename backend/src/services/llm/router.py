"""LLM Task Router.

The core routing engine that inspects request parameters and dynamically
selects the most appropriate LLM provider. Routes simple generation tasks
to fast models (Groq/Llama) and complex reasoning tasks (analysis, security)
to frontier models (OpenAI/Gemini).

Design:
  - FAST tasks: boilerplate, docstring, format, unit_test, refactor
    → Specialized fast model (Groq Llama3)
  - COMPLEX tasks: bug_hunt, security_audit, code_review, analyze endpoint
    → Reasoning frontier model (OpenAI GPT-4o / Gemini)
  - Fallback chain: primary → secondary → error
"""

import logging
from enum import Enum

import httpx

from src.services.llm.base import BaseLLMProvider, LLMResponse
from src.services.llm.groq_provider import GroqProvider
from src.services.llm.openai_provider import OpenAIProvider
from src.services.llm.gemini_provider import GeminiProvider
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Task types that use the fast model
FAST_TASKS = {
    "boilerplate",
    "docstring",
    "format",
    "unit_test",
    "translate",
    "completion",
}

# Task types that require reasoning model
REASONING_TASKS = {
    "bug_hunt",
    "security_audit",
    "code_review",
    "refactor",
    "architecture_review",
    "performance_audit",
}


class RouterMode(str, Enum):
    FAST = "fast"
    REASONING = "reasoning"


class TaskRouter:
    """
    Routes LLM tasks to the optimal provider based on:
    - task_type: Explicit routing hints
    - endpoint: /analyze always uses reasoning
    - prompt_length: Long prompts (> 2000 chars) use reasoning model
    """

    def __init__(self):
        self._fast_providers: list[BaseLLMProvider] = []
        self._reasoning_providers: list[BaseLLMProvider] = []
        self._initialize_providers()

    def _initialize_providers(self):
        groq_fast = GroqProvider(model=settings.groq_fast_model)
        groq_reasoning = GroqProvider(model=settings.groq_reasoning_model)
        openai = OpenAIProvider()
        gemini = GeminiProvider()

        fast_pref = settings.fast_provider.lower()
        reasoning_pref = settings.reasoning_provider.lower()

        # Fast chain
        if fast_pref == "groq":
            self._fast_providers = [groq_fast, gemini, openai]
        else:
            self._fast_providers = [gemini, groq_fast, openai]

        # Reasoning chain
        if reasoning_pref == "openai":
            self._reasoning_providers = [openai, gemini, groq_reasoning]
        elif reasoning_pref == "gemini":
            self._reasoning_providers = [gemini, openai, groq_reasoning]
        else:
            self._reasoning_providers = [groq_reasoning, openai, gemini]

        logger.info(
            "Router initialized | fast=%s | reasoning=%s",
            [p.provider_name for p in self._fast_providers],
            [p.provider_name for p in self._reasoning_providers],
        )

    def _select_mode(
        self,
        task_type: str,
        endpoint: str = "generate",
        prompt_length: int = 0,
    ) -> RouterMode:
        """Determine routing mode from request characteristics."""
        task_lower = task_type.lower().replace("-", "_").replace(" ", "_")

        # Analysis endpoint always uses reasoning model
        if endpoint == "analyze":
            return RouterMode.REASONING

        # Explicit task type routing
        if task_lower in REASONING_TASKS:
            return RouterMode.REASONING

        if task_lower in FAST_TASKS:
            return RouterMode.FAST

        # Heuristic: long prompts need more capability
        if prompt_length > 2000:
            return RouterMode.REASONING

        # Default to fast for generation
        return RouterMode.FAST

    async def route(
        self,
        task_type: str,
        system_prompt: str,
        user_message: str,
        endpoint: str = "generate",
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Route request to optimal provider with automatic fallback.

        Tries each provider in the preferred chain. Falls back to next
        provider if one fails due to rate limits or unavailability.

        Raises:
            RuntimeError: If all providers in the chain fail.
        """
        prompt_length = len(system_prompt) + len(user_message)
        mode = self._select_mode(task_type, endpoint, prompt_length)

        if mode == RouterMode.FAST:
            providers = self._fast_providers
            logger.info("Router: task_type=%s → FAST chain", task_type)
        else:
            providers = self._reasoning_providers
            logger.info("Router: task_type=%s → REASONING chain", task_type)

        last_error = None
        for provider in providers:
            try:
                logger.info("Attempting provider: %s (%s)", provider.provider_name, provider.model_name)
                response = await provider.generate(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                logger.info("Success with provider: %s", provider.provider_name)
                return response
            except ValueError as e:
                # API key not configured — skip silently
                logger.debug("Provider %s not configured: %s", provider.provider_name, e)
                last_error = e
                continue
            except httpx.TimeoutException as e:
                logger.warning("Provider %s timed out: %s", provider.provider_name, e)
                last_error = e
                continue
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in (400, 401, 403, 404, 422, 429, 500, 502, 503, 504):
                    logger.warning(
                        "Provider %s returned %d, trying fallback: %s",
                        provider.provider_name, status, e
                    )
                    last_error = e
                    continue
                # Non-retriable HTTP error — raise immediately
                raise

        raise RuntimeError(
            f"All LLM providers failed for task_type='{task_type}'. "
            f"Last error: {last_error}"
        ) from last_error
