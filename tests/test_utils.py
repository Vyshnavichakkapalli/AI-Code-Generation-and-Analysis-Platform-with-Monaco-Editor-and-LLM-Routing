"""Unit tests for code utility functions."""

import pytest
from src.utils.code_utils import strip_markdown_fences, parse_llm_json_response


class TestStripMarkdownFences:
    def test_strips_named_python_fence(self):
        text = "```python\nprint('hello')\n```"
        assert strip_markdown_fences(text) == "print('hello')"

    def test_strips_named_javascript_fence(self):
        text = "```javascript\nconsole.log('hi');\n```"
        assert strip_markdown_fences(text) == "console.log('hi');"

    def test_strips_generic_fence(self):
        text = "```\nsome code here\n```"
        assert strip_markdown_fences(text) == "some code here"

    def test_returns_raw_when_no_fence(self):
        text = "def hello():\n    return 'world'"
        assert strip_markdown_fences(text) == text

    def test_handles_empty_string(self):
        assert strip_markdown_fences("") == ""

    def test_handles_multiline_code(self):
        text = "```python\ndef foo():\n    x = 1\n    return x\n```"
        result = strip_markdown_fences(text)
        assert "def foo():" in result
        assert "```" not in result

    def test_handles_trailing_whitespace(self):
        text = "```python\ncode here\n```   "
        result = strip_markdown_fences(text)
        assert "code here" in result
        assert "```" not in result


class TestParseLLMJsonResponse:
    def test_parses_valid_json_array(self):
        text = '[{"issue_type": "bug", "description": "null pointer", "suggested_fix": "check null", "severity": "high"}]'
        result = parse_llm_json_response(text)
        assert len(result) == 1
        assert result[0]["issue_type"] == "bug"

    def test_returns_default_on_invalid_json(self):
        result = parse_llm_json_response("not valid json", default=[])
        assert result == []

    def test_returns_empty_on_empty_string(self):
        result = parse_llm_json_response("")
        assert result == []

    def test_extracts_json_from_surrounding_text(self):
        text = 'Here are the issues: [{"issue_type": "warning", "description": "test", "suggested_fix": "fix", "severity": "low"}] Thank you.'
        result = parse_llm_json_response(text)
        assert len(result) == 1

    def test_strips_fence_before_parsing(self):
        text = '```json\n[{"issue_type": "error", "description": "msg", "suggested_fix": "fix", "severity": "high"}]\n```'
        result = parse_llm_json_response(text)
        assert len(result) == 1
        assert result[0]["issue_type"] == "error"

    def test_handles_multiple_issues(self):
        text = '[{"issue_type": "a", "description": "desc1", "suggested_fix": "fix1", "severity": "low"}, {"issue_type": "b", "description": "desc2", "suggested_fix": "fix2", "severity": "high"}]'
        result = parse_llm_json_response(text)
        assert len(result) == 2
