"""Utility functions for code processing."""

import re
import logging

logger = logging.getLogger(__name__)


def strip_markdown_fences(text: str) -> str:
    """
    Strip markdown code fences from LLM output.

    LLMs frequently wrap generated code in markdown fences like:
        ```python
        <code here>
        ```

    This function extracts the raw code content, trying:
    1. Named fences (```python ... ```)
    2. Generic fences (``` ... ```)
    3. Returning the original text if no fences found

    Args:
        text: Raw LLM output that may contain markdown fences.

    Returns:
        Cleaned source code string.
    """
    if not text:
        return ""

    text = text.strip()

    # Pattern 1: Named fence with language identifier
    named_fence_pattern = re.compile(
        r"^```[a-zA-Z0-9_+-]*\n(.*?)^```\s*$",
        re.MULTILINE | re.DOTALL,
    )
    match = named_fence_pattern.search(text)
    if match:
        return match.group(1).strip()

    # Pattern 2: Generic fence without language identifier
    generic_fence_pattern = re.compile(
        r"^```\n(.*?)^```\s*$",
        re.MULTILINE | re.DOTALL,
    )
    match = generic_fence_pattern.search(text)
    if match:
        return match.group(1).strip()

    # Pattern 3: Inline backtick fences (single line)
    inline_pattern = re.compile(r"^`([^`]+)`$")
    match = inline_pattern.match(text)
    if match:
        return match.group(1).strip()

    # No fences found — return as-is
    return text


def extract_json_from_llm_output(text: str) -> str:
    """
    Extract JSON content from LLM output that may contain extra text.

    LLMs sometimes prefix JSON arrays/objects with conversational text.
    This function finds the first valid JSON array or object in the output.

    Args:
        text: Raw LLM response text.

    Returns:
        Extracted JSON string, or the original text if not found.
    """
    if not text:
        return "[]"

    text = text.strip()

    # Try to find JSON array
    array_match = re.search(r"\[.*\]", text, re.DOTALL)
    if array_match:
        return array_match.group(0)

    # Try to find JSON object
    obj_match = re.search(r"\{.*\}", text, re.DOTALL)
    if obj_match:
        return obj_match.group(0)

    return text


def parse_llm_json_response(text: str, default: list | None = None) -> list:
    """
    Parse a JSON array from LLM output with robust error handling.

    Args:
        text: Raw LLM response that should contain a JSON array.
        default: Default value if parsing fails (defaults to []).

    Returns:
        Parsed list or default value.
    """
    import json

    if default is None:
        default = []

    if not text:
        return default

    # Strip markdown fences first
    cleaned = strip_markdown_fences(text)

    # Extract JSON from potential surrounding text
    json_str = extract_json_from_llm_output(cleaned)

    try:
        result = json.loads(json_str)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return [result]
        else:
            logger.warning("LLM JSON parsed but not a list: %s", type(result))
            return default
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse LLM JSON response: %s | text: %s", e, text[:200])
        return default
