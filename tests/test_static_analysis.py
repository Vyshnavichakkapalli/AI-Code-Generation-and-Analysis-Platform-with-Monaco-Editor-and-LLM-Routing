"""Unit tests for the static analysis engine."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.analysis.static_analyzer import (
    _normalize_pylint_output,
    _normalize_eslint_output,
    run_static_analysis,
)


class TestNormalizePylintOutput:
    def test_parses_valid_pylint_json(self):
        raw = '[{"line": 5, "column": 0, "type": "convention", "message": "Missing function docstring", "symbol": "C0116", "message-id": "C0116"}]'
        result = _normalize_pylint_output(raw)
        assert len(result) == 1
        assert result[0]["line_number"] == 5
        assert result[0]["type"] == "convention"
        assert "Missing function docstring" in result[0]["message"]

    def test_handles_empty_output(self):
        result = _normalize_pylint_output("")
        assert result == []

    def test_handles_invalid_json(self):
        result = _normalize_pylint_output("not json at all")
        assert result == []

    def test_handles_multiple_issues(self):
        raw = '[{"line": 1, "column": 0, "type": "error", "message": "E1", "symbol": "e1", "message-id": "E1"}, {"line": 2, "column": 4, "type": "warning", "message": "W1", "symbol": "w1", "message-id": "W1"}]'
        result = _normalize_pylint_output(raw)
        assert len(result) == 2


class TestNormalizeESLintOutput:
    def test_parses_valid_eslint_json(self):
        raw = '[{"filePath": "test.js", "messages": [{"line": 3, "column": 5, "severity": 2, "message": "Unexpected var", "ruleId": "no-var"}]}]'
        result = _normalize_eslint_output(raw)
        assert len(result) == 1
        assert result[0]["line_number"] == 3
        assert result[0]["type"] == "error"

    def test_handles_empty_messages(self):
        raw = '[{"filePath": "test.js", "messages": []}]'
        result = _normalize_eslint_output(raw)
        assert result == []

    def test_handles_invalid_json(self):
        result = _normalize_eslint_output("invalid")
        assert result == []


@pytest.mark.asyncio
class TestRunStaticAnalysis:
    async def test_unsupported_language_returns_empty(self):
        """Unsupported languages return empty list without error."""
        result = await run_static_analysis("SELECT * FROM users;", "sql")
        assert result == []

    async def test_python_analysis_runs(self):
        """Python analysis should run pylint on valid code."""
        code = "def foo():\n    x = 1\n    return x\n"
        with patch("src.services.analysis.static_analyzer._run_pylint") as mock_pylint:
            mock_pylint.return_value = []
            result = await run_static_analysis(code, "python")
        assert isinstance(result, list)
        mock_pylint.assert_called_once()

    async def test_temp_file_cleaned_up(self):
        """Temp files must be deleted after analysis."""
        import tempfile
        import glob

        before = set(glob.glob(os.path.join(tempfile.gettempdir(), "codeai_analysis_*")))

        with patch("src.services.analysis.static_analyzer._run_pylint") as mock_pylint:
            mock_pylint.return_value = []
            await run_static_analysis("x = 1", "python")

        after = set(glob.glob(os.path.join(tempfile.gettempdir(), "codeai_analysis_*")))
        # No new temp files should remain
        new_files = after - before
        assert len(new_files) == 0, f"Temp files not cleaned up: {new_files}"
