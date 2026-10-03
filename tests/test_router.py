"""Unit tests for the LLM routing engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.llm.router import TaskRouter, RouterMode, FAST_TASKS, REASONING_TASKS


class TestTaskRouterModeSelection:
    """Test the routing decision logic."""

    def setup_method(self):
        with patch("src.services.llm.router.GroqProvider"), \
             patch("src.services.llm.router.OpenAIProvider"), \
             patch("src.services.llm.router.GeminiProvider"):
            self.router = TaskRouter()

    def test_boilerplate_uses_fast_mode(self):
        mode = self.router._select_mode("boilerplate", "generate")
        assert mode == RouterMode.FAST

    def test_docstring_uses_fast_mode(self):
        mode = self.router._select_mode("docstring", "generate")
        assert mode == RouterMode.FAST

    def test_format_uses_fast_mode(self):
        mode = self.router._select_mode("format", "generate")
        assert mode == RouterMode.FAST

    def test_unit_test_uses_fast_mode(self):
        mode = self.router._select_mode("unit_test", "generate")
        assert mode == RouterMode.FAST

    def test_bug_hunt_uses_reasoning_mode(self):
        mode = self.router._select_mode("bug_hunt", "generate")
        assert mode == RouterMode.REASONING

    def test_security_audit_uses_reasoning_mode(self):
        mode = self.router._select_mode("security_audit", "generate")
        assert mode == RouterMode.REASONING

    def test_analyze_endpoint_always_reasoning(self):
        """Analysis endpoint always forces reasoning model regardless of task_type."""
        mode = self.router._select_mode("boilerplate", "analyze")
        assert mode == RouterMode.REASONING

    def test_long_prompt_uses_reasoning(self):
        """Prompts longer than 2000 chars are routed to reasoning model."""
        mode = self.router._select_mode("unknown_task", "generate", prompt_length=2500)
        assert mode == RouterMode.REASONING

    def test_short_unknown_task_uses_fast(self):
        """Unknown short tasks default to fast model."""
        mode = self.router._select_mode("unknown_task", "generate", prompt_length=100)
        assert mode == RouterMode.FAST


@pytest.mark.asyncio
class TestTaskRouterFallback:
    """Test provider fallback behavior."""

    async def test_falls_back_to_second_provider(self):
        """If first provider fails, should try second provider."""
        first_provider = AsyncMock()
        first_provider.provider_name = "groq"
        first_provider.model_name = "llama3-8b-8192"
        first_provider.generate.side_effect = ValueError("API key not configured")

        second_provider = AsyncMock()
        second_provider.provider_name = "gemini"
        second_provider.model_name = "gemini-2.0-flash"
        mock_response = MagicMock()
        mock_response.content = "def hello(): pass"
        mock_response.model = "gemini-2.0-flash"
        mock_response.provider = "gemini"
        second_provider.generate.return_value = mock_response

        with patch("src.services.llm.router.GroqProvider"), \
             patch("src.services.llm.router.OpenAIProvider"), \
             patch("src.services.llm.router.GeminiProvider"):
            router = TaskRouter()
            router._fast_providers = [first_provider, second_provider]
            router._reasoning_providers = [second_provider, first_provider]

        result = await router.route(
            task_type="boilerplate",
            system_prompt="You are a code generator",
            user_message="Write hello world",
            endpoint="generate",
        )

        assert result.provider == "gemini"
        first_provider.generate.assert_called_once()
        second_provider.generate.assert_called_once()

    async def test_raises_when_all_providers_fail(self):
        """Should raise RuntimeError when all providers fail."""
        provider = AsyncMock()
        provider.provider_name = "test"
        provider.model_name = "test-model"
        provider.generate.side_effect = ValueError("No key")

        with patch("src.services.llm.router.GroqProvider"), \
             patch("src.services.llm.router.OpenAIProvider"), \
             patch("src.services.llm.router.GeminiProvider"):
            router = TaskRouter()
            router._fast_providers = [provider]
            router._reasoning_providers = [provider]

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            await router.route(
                task_type="boilerplate",
                system_prompt="sys",
                user_message="user",
                endpoint="generate",
            )
