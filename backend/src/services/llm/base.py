"""Abstract base class for LLM providers.

Defines the interface that all LLM provider implementations must follow,
enabling clean substitution (Strategy Pattern).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Normalized response from any LLM provider."""
    content: str
    model: str
    provider: str
    usage: dict | None = None


class BaseLLMProvider(ABC):
    """Abstract interface that all LLM provider clients must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier string."""
        ...

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Call the LLM and return a normalized LLMResponse.

        Raises:
            httpx.TimeoutException: On timeout.
            httpx.HTTPStatusError: On API error.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name})"
