"""Integration tests for the REST API endpoints.

Uses mocked LLM providers to avoid real API calls during testing.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
class TestGenerateEndpoint:
    async def test_generate_returns_correct_schema(self, client):
        """Test that /generate returns the required response schema."""
        mock_llm_response = MagicMock()
        mock_llm_response.content = "def hello():\n    return 'world'"
        mock_llm_response.model = "llama3-8b-8192"
        mock_llm_response.provider = "groq"

        with patch("src.routes.generate.task_router.route", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = mock_llm_response

            response = await client.post(
                "/api/v1/generate",
                json={
                    "prompt": "Write a hello world function in Python",
                    "language": "python",
                    "task_type": "boilerplate",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "routed_model" in data
        assert "request_id" in data
        assert "explanation" in data

    async def test_generate_strips_markdown_fences(self, client):
        """Test that markdown fences are stripped from generated code."""
        mock_llm_response = MagicMock()
        mock_llm_response.content = "```python\ndef hello():\n    return 'world'\n```"
        mock_llm_response.model = "llama3-8b-8192"
        mock_llm_response.provider = "groq"

        with patch("src.routes.generate.task_router.route", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = mock_llm_response

            response = await client.post(
                "/api/v1/generate",
                json={
                    "prompt": "Write a hello world function",
                    "language": "python",
                    "task_type": "boilerplate",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "```" not in data["code"]
        assert "def hello():" in data["code"]

    async def test_generate_requires_prompt(self, client):
        """Test validation: prompt is required."""
        response = await client.post(
            "/api/v1/generate",
            json={"language": "python", "task_type": "boilerplate"},
        )
        assert response.status_code == 422

    async def test_generate_requires_language(self, client):
        """Test validation: language is required."""
        response = await client.post(
            "/api/v1/generate",
            json={"prompt": "Write code", "task_type": "boilerplate"},
        )
        assert response.status_code == 422

    async def test_generate_handles_llm_failure(self, client):
        """Test that LLM failure returns 503 gracefully."""
        with patch("src.routes.generate.task_router.route", new_callable=AsyncMock) as mock_route:
            mock_route.side_effect = RuntimeError("All providers failed")

            response = await client.post(
                "/api/v1/generate",
                json={
                    "prompt": "Write code",
                    "language": "python",
                    "task_type": "boilerplate",
                },
            )

        assert response.status_code == 503


@pytest.mark.asyncio
class TestAnalyzeEndpoint:
    async def test_analyze_returns_correct_schema(self, client):
        """Test that /analyze returns the required response schema."""
        mock_llm_response = MagicMock()
        mock_llm_response.content = '[{"issue_type": "bug", "description": "Unused variable", "suggested_fix": "Remove it", "severity": "low"}]'
        mock_llm_response.model = "gpt-4o-mini"
        mock_llm_response.provider = "openai"

        with patch("src.routes.analyze.task_router.route", new_callable=AsyncMock) as mock_route, \
             patch("src.routes.analyze.run_static_analysis", new_callable=AsyncMock) as mock_static:
            mock_route.return_value = mock_llm_response
            mock_static.return_value = [
                {"line_number": 1, "column": 0, "type": "warning", "message": "Missing docstring", "rule": "C0114"}
            ]

            response = await client.post(
                "/api/v1/analyze",
                json={
                    "code": "def foo():\n    x = 1\n    return x",
                    "language": "python",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "static_analysis" in data
        assert "llm_feedback" in data
        assert "routed_model" in data
        assert "request_id" in data
        assert isinstance(data["static_analysis"], list)
        assert isinstance(data["llm_feedback"], list)

    async def test_analyze_static_analysis_format(self, client):
        """Test that static_analysis items have line_number and message."""
        mock_llm_response = MagicMock()
        mock_llm_response.content = "[]"
        mock_llm_response.model = "gpt-4o-mini"
        mock_llm_response.provider = "openai"

        with patch("src.routes.analyze.task_router.route", new_callable=AsyncMock) as mock_route, \
             patch("src.routes.analyze.run_static_analysis", new_callable=AsyncMock) as mock_static:
            mock_route.return_value = mock_llm_response
            mock_static.return_value = [
                {"line_number": 3, "column": 0, "type": "error", "message": "Syntax error", "rule": "E0001"}
            ]

            response = await client.post(
                "/api/v1/analyze",
                json={"code": "x = ", "language": "python"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["static_analysis"]) == 1
        issue = data["static_analysis"][0]
        assert "line_number" in issue
        assert "message" in issue

    async def test_analyze_requires_code(self, client):
        """Test validation: code is required."""
        response = await client.post(
            "/api/v1/analyze",
            json={"language": "python"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestHistoryEndpoint:
    async def test_history_returns_correct_schema(self, client):
        """Test that /history returns an array of objects representing past requests."""
        response = await client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_history_pagination(self, client):
        """Test that limit and offset parameters work."""
        response = await client.get("/api/v1/history?limit=10&offset=0")
        assert response.status_code == 200

    async def test_history_invalid_limit(self, client):
        """Test that invalid limit returns 422."""
        response = await client.get("/api/v1/history?limit=0")
        assert response.status_code == 422
