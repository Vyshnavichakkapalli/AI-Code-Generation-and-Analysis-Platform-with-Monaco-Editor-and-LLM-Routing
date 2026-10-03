"""Prompt Template Manager.

Loads prompt templates from an external JSON configuration file,
decoupling prompt engineering from core routing logic.
"""

import json
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

TEMPLATES_PATH = Path(__file__).parent / "templates.json"


@lru_cache(maxsize=1)
def _load_templates() -> dict:
    """Load and cache templates from JSON file."""
    try:
        with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Prompt templates file not found at %s", TEMPLATES_PATH)
        return {}
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in templates file: %s", e)
        return {}


def get_generation_prompt(
    task_type: str,
    language: str,
    prompt: str,
    code_context: str = "",
) -> tuple[str, str]:
    """
    Returns (system_prompt, user_message) for a generation request.

    Falls back to 'default' template if the specific task_type is not found.
    """
    templates = _load_templates()
    gen_templates = templates.get("generation", {})

    task_key = task_type.lower().replace(" ", "_").replace("-", "_")
    template = gen_templates.get(task_key, gen_templates.get("default", {}))

    if not template:
        logger.warning("No template found for task_type=%s, using empty strings", task_type)
        return "", prompt

    system_prompt = template.get("system", "")
    user_template = template.get("user_template", "{prompt}")

    user_message = user_template.format(
        language=language,
        prompt=prompt,
        code_context=code_context or "(none provided)",
    )

    return system_prompt, user_message


def get_analysis_prompt(
    task_type: str,
    language: str,
    code: str,
) -> tuple[str, str]:
    """
    Returns (system_prompt, user_message) for an analysis request.

    Falls back to 'default' template if the specific task_type is not found.
    """
    templates = _load_templates()
    analysis_templates = templates.get("analysis", {})

    task_key = task_type.lower().replace(" ", "_").replace("-", "_")
    template = analysis_templates.get(task_key, analysis_templates.get("default", {}))

    if not template:
        logger.warning("No template found for task_type=%s, using empty strings", task_type)
        return "", code

    system_prompt = template.get("system", "")
    user_template = template.get("user_template", "Analyze this code:\n{code}")

    user_message = user_template.format(
        language=language,
        code=code,
    )

    return system_prompt, user_message
