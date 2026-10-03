"""Code Analysis API Route.

POST /api/v1/analyze
- Concurrently runs static analysis (Pylint/ESLint) AND LLM review
- Synthesizes both outputs into a unified response
- Always routes to reasoning model for deep code analysis
- Persists combined payload to PostgreSQL
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.history import RequestHistory
from src.routes.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    StaticAnalysisIssue,
    LLMFeedbackIssue,
    ErrorResponse,
)
from src.services.llm.router import TaskRouter
from src.services.analysis.static_analyzer import run_static_analysis
from src.prompts.manager import get_analysis_prompt
from src.utils.code_utils import parse_llm_json_response

logger = logging.getLogger(__name__)

router = APIRouter()
task_router = TaskRouter()


def _map_llm_feedback(raw_issues: list) -> list[LLMFeedbackIssue]:
    """Normalize raw LLM JSON output into LLMFeedbackIssue objects."""
    results = []
    for item in raw_issues:
        if not isinstance(item, dict):
            continue
        results.append(
            LLMFeedbackIssue(
                issue_type=str(item.get("issue_type", item.get("type", "issue"))),
                description=str(item.get("description", item.get("message", ""))),
                suggested_fix=str(item.get("suggested_fix", item.get("fix", "No fix suggested"))),
                severity=str(item.get("severity", "medium")),
            )
        )
    return results


def _map_static_issues(raw_issues: list) -> list[StaticAnalysisIssue]:
    """Normalize raw static analysis output into StaticAnalysisIssue objects."""
    return [
        StaticAnalysisIssue(
            line_number=int(issue.get("line_number", 0)),
            message=str(issue.get("message", "")),
            column=issue.get("column"),
            type=issue.get("type"),
            rule=issue.get("rule"),
        )
        for issue in raw_issues
        if isinstance(issue, dict)
    ]


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        502: {"model": ErrorResponse, "description": "Upstream LLM provider failure"},
        503: {"model": ErrorResponse, "description": "All LLM providers unavailable"},
    },
    summary="Analyze code with static tools and LLM review",
)
async def analyze_code(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """
    Perform a comprehensive analysis of submitted code.

    Concurrently runs:
    1. **Static analysis** (Pylint for Python, ESLint for JS) — deterministic
    2. **LLM reasoning review** (always uses frontier model) — subjective

    Both results are synthesized into a unified response payload.
    """
    request_id = str(uuid.uuid4())
    logger.info(
        "Analyze request | id=%s | language=%s | task_type=%s | code_length=%d",
        request_id, request.language, request.task_type, len(request.code)
    )

    task_type = request.task_type or "code_review"

    # Build analysis prompt
    system_prompt, user_message = get_analysis_prompt(
        task_type=task_type,
        language=request.language,
        code=request.code,
    )

    try:
        # Run static analysis and LLM review CONCURRENTLY
        static_task = run_static_analysis(request.code, request.language)
        llm_task = task_router.route(
            task_type=task_type,
            system_prompt=system_prompt,
            user_message=user_message,
            endpoint="analyze",  # Forces reasoning model
        )

        static_raw, llm_response = await asyncio.gather(
            static_task,
            llm_task,
            return_exceptions=True,
        )

    except Exception as e:
        logger.error("Unexpected error during concurrent analysis: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    # Handle static analysis errors gracefully
    if isinstance(static_raw, Exception):
        logger.error("Static analysis failed: %s", static_raw)
        static_issues = []
    else:
        static_issues = _map_static_issues(static_raw)

    # Handle LLM errors — return 503 with clear message
    if isinstance(llm_response, Exception):
        logger.error("LLM analysis failed: %s", llm_response)
        if isinstance(llm_response, RuntimeError):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Service Unavailable",
                    "detail": "All LLM providers are currently unavailable.",
                    "code": "LLM_UNAVAILABLE",
                },
            )
        elif isinstance(llm_response, httpx.TimeoutException):
            raise HTTPException(
                status_code=504,
                detail={
                    "error": "Gateway Timeout",
                    "detail": "LLM provider timed out during analysis.",
                    "code": "LLM_TIMEOUT",
                },
            )
        raise HTTPException(status_code=502, detail="LLM provider error during analysis")

    # Parse LLM JSON feedback
    raw_llm_issues = parse_llm_json_response(llm_response.content, default=[])
    llm_feedback = _map_llm_feedback(raw_llm_issues)

    routed_model = f"{llm_response.provider}/{llm_response.model}"

    # Build combined response payload
    response_payload = {
        "static_analysis": [issue.model_dump() for issue in static_issues],
        "llm_feedback": [issue.model_dump() for issue in llm_feedback],
        "routed_model": routed_model,
        "request_id": request_id,
    }

    # Persist to database
    history_record = RequestHistory(
        id=request_id,
        endpoint_used="analyze",
        language=request.language,
        task_type=task_type,
        user_input=request.code[:5000],  # Truncate large code for storage
        model_routed_to=routed_model,
        response_payload=response_payload,
        created_at=datetime.now(timezone.utc),
    )
    db.add(history_record)
    await db.commit()

    logger.info(
        "Analysis complete | id=%s | static_issues=%d | llm_issues=%d | model=%s",
        request_id, len(static_issues), len(llm_feedback), routed_model
    )

    return AnalyzeResponse(
        static_analysis=static_issues,
        llm_feedback=llm_feedback,
        routed_model=routed_model,
        request_id=request_id,
    )
