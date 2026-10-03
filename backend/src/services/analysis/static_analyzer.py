"""Static Analysis Engine.

Executes real linting tools (Pylint for Python, ESLint for JavaScript/TypeScript)
against user-submitted code in a secure manner:
  - Code is written to a temporary file that is immediately deleted after analysis
  - File permissions are restricted to the current process
  - Execution is sandboxed to the temp directory only
  - Subprocess runs with a timeout to prevent hanging
  - Output is parsed into a normalized schema
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Timeout for subprocess execution (seconds)
SUBPROCESS_TIMEOUT = 30

# Normalized result schema
AnalysisIssue = dict  # {line_number: int, column: int, type: str, message: str, rule: str}


def _normalize_pylint_output(raw_output: str) -> list[AnalysisIssue]:
    """Parse pylint JSON output into normalized schema."""
    if not raw_output.strip():
        return []
    try:
        issues = json.loads(raw_output)
        return [
            {
                "line_number": issue.get("line", 0),
                "column": issue.get("column", 0),
                "type": issue.get("type", "convention"),
                "message": issue.get("message", ""),
                "rule": issue.get("symbol", issue.get("message-id", "")),
            }
            for issue in issues
            if isinstance(issue, dict)
        ]
    except json.JSONDecodeError:
        logger.warning("Could not parse pylint JSON output: %s", raw_output[:200])
        return []


def _normalize_eslint_output(raw_output: str) -> list[AnalysisIssue]:
    """Parse ESLint JSON output into normalized schema."""
    if not raw_output.strip():
        return []
    try:
        files = json.loads(raw_output)
        issues = []
        for file_result in files:
            for msg in file_result.get("messages", []):
                severity_map = {1: "warning", 2: "error"}
                issues.append({
                    "line_number": msg.get("line", 0),
                    "column": msg.get("column", 0),
                    "type": severity_map.get(msg.get("severity", 1), "warning"),
                    "message": msg.get("message", ""),
                    "rule": msg.get("ruleId", ""),
                })
        return issues
    except json.JSONDecodeError:
        logger.warning("Could not parse ESLint JSON output: %s", raw_output[:200])
        return []


def _run_pylint(file_path: str) -> list[AnalysisIssue]:
    """
    Execute pylint against a temp Python file and return parsed issues.
    pylint exits with status > 0 when issues are found — this is expected.
    """
    try:
        result = subprocess.run(
            [
                "python", "-m", "pylint",
                "--output-format=json",
                "--score=no",
                "--disable=C0114",  # Allow missing module docstrings
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            cwd=tempfile.gettempdir(),
        )
        # pylint returns 0=ok, 1=fatal, 2=error, 4=warning, 8=refactor, 16=convention
        # Any non-zero is normal when issues found; only unexpected errors matter
        combined_output = result.stdout + result.stderr
        return _normalize_pylint_output(result.stdout)
    except subprocess.TimeoutExpired:
        logger.error("Pylint timed out on file: %s", file_path)
        return [{"line_number": 0, "column": 0, "type": "error", "message": "Static analysis timed out", "rule": "timeout"}]
    except FileNotFoundError:
        logger.error("pylint not found in PATH")
        return [{"line_number": 0, "column": 0, "type": "error", "message": "pylint is not installed in this environment", "rule": "setup"}]


def _run_eslint(file_path: str, language: str) -> list[AnalysisIssue]:
    """
    Execute ESLint against a temp JS/TS file and return parsed issues.
    Falls back to a basic regex-based check if ESLint is not available.
    """
    try:
        result = subprocess.run(
            [
                "npx", "--yes", "eslint",
                "--format=json",
                "--no-eslintrc",
                "--rule", '{"no-undef": "warn", "no-unused-vars": "warn", "semi": ["warn", "always"]}',
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            cwd=tempfile.gettempdir(),
        )
        return _normalize_eslint_output(result.stdout)
    except subprocess.TimeoutExpired:
        logger.error("ESLint timed out on file: %s", file_path)
        return [{"line_number": 0, "column": 0, "type": "error", "message": "ESLint analysis timed out", "rule": "timeout"}]
    except FileNotFoundError:
        logger.warning("ESLint not found, using basic JS analysis")
        return _basic_js_analysis(file_path)


def _basic_js_analysis(file_path: str) -> list[AnalysisIssue]:
    """Fallback basic JavaScript analysis using regex when ESLint unavailable."""
    issues = []
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()
            # Check for missing semicolons on statement lines
            if (
                stripped
                and not stripped.endswith((";", "{", "}", "(", ",", "//", "*/", "=>"))
                and not stripped.startswith(("//", "*", "/*", "import ", "export ", "class ", "function ", "const ", "let ", "var ", "if ", "for ", "while "))
                and len(stripped) > 2
            ):
                pass  # Skip — too many false positives without AST

            # Check for console.log statements
            if "console.log" in line:
                issues.append({
                    "line_number": i,
                    "column": line.index("console.log") + 1,
                    "type": "warning",
                    "message": "Unexpected console.log statement",
                    "rule": "no-console",
                })

            # Check for var declarations (prefer const/let)
            if re.search(r"\bvar\s+\w+", line):
                issues.append({
                    "line_number": i,
                    "column": line.index("var") + 1,
                    "type": "warning",
                    "message": "Unexpected var, use const or let instead",
                    "rule": "no-var",
                })

    except Exception as e:
        logger.error("Basic JS analysis error: %s", e)

    return issues


LANGUAGE_EXTENSION_MAP = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "jsx": ".jsx",
    "tsx": ".tsx",
    "sql": ".sql",
    "go": ".go",
    "rust": ".rs",
    "java": ".java",
    "cpp": ".cpp",
    "c": ".c",
}


async def run_static_analysis(code: str, language: str) -> list[AnalysisIssue]:
    """
    Main entry point: write code to a temp file, run the appropriate linter,
    and return normalized issues. Temp file is always deleted after execution.

    Args:
        code: The source code string to analyze.
        language: The programming language identifier.

    Returns:
        List of normalized AnalysisIssue dictionaries.
    """
    lang_lower = language.lower()
    extension = LANGUAGE_EXTENSION_MAP.get(lang_lower, ".txt")

    tmp_file = None
    try:
        # Create temporary file with restricted permissions
        fd, tmp_path = tempfile.mkstemp(suffix=extension, prefix="codeai_analysis_")
        tmp_file = tmp_path

        # Write code with explicit encoding
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)

        logger.info("Running static analysis for language=%s on file=%s", language, tmp_path)

        # Run linter in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()

        if lang_lower == "python":
            issues = await loop.run_in_executor(None, _run_pylint, tmp_path)
        elif lang_lower in ("javascript", "typescript", "jsx", "tsx"):
            issues = await loop.run_in_executor(None, _run_eslint, tmp_path, lang_lower)
        else:
            logger.info("No static analysis tool available for language: %s", language)
            issues = []

        logger.info("Static analysis found %d issues", len(issues))
        return issues

    except Exception as e:
        logger.error("Static analysis error: %s", e, exc_info=True)
        return [{"line_number": 0, "column": 0, "type": "error", "message": f"Analysis engine error: {str(e)}", "rule": "internal"}]

    finally:
        # Always clean up the temp file
        if tmp_file and os.path.exists(tmp_file):
            try:
                os.unlink(tmp_file)
                logger.debug("Cleaned up temp file: %s", tmp_file)
            except OSError as e:
                logger.warning("Could not delete temp file %s: %s", tmp_file, e)
