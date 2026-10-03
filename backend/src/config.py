"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/codeai"
    sync_database_url: str = "postgresql://postgres:postgres@db:5432/codeai"

    # LLM Providers
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_fast_model: str = "openai/gpt-oss-20b"
    groq_reasoning_model: str = "openai/gpt-oss-120b"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_reasoning_model: str = "gpt-4o-mini"

    # Fallback: Gemini (Google)
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    gemini_reasoning_model: str = "gemini-2.0-flash"

    # Together.ai fallback
    together_api_key: str = ""
    together_base_url: str = "https://api.together.xyz/v1"
    together_fast_model: str = "meta-llama/Llama-3-8b-chat-hf"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://frontend:5173"

    # LLM timeouts
    llm_timeout: int = 60
    llm_max_retries: int = 3

    # Active providers (comma-separated, in priority order)
    # E.g. "groq,openai" or "groq,gemini"
    fast_provider: str = "groq"
    reasoning_provider: str = "openai"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
