"""Code Generation API Route.

POST /api/v1/generate
- Routes to fast LLM for simple generation, reasoning model for complex tasks
- Strips markdown fences from LLM output
- Persists request/response to PostgreSQL
"""

import logging
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.history import RequestHistory
from src.routes.schemas import GenerateRequest, GenerateResponse, ErrorResponse
from src.services.llm.router import TaskRouter
from src.prompts.manager import get_generation_prompt
from src.utils.code_utils import strip_markdown_fences

logger = logging.getLogger(__name__)

router = APIRouter()
task_router = TaskRouter()


@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        502: {"model": ErrorResponse, "description": "Upstream LLM provider failure"},
        503: {"model": ErrorResponse, "description": "All LLM providers unavailable"},
    },
    summary="Generate code from a natural language prompt",
)
async def generate_code(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> GenerateResponse:
    """
    Generate code based on a natural language instruction.

    The routing engine selects either:
    - **Fast model** (Groq/Llama3) for: boilerplate, docstring, format, unit_test
    - **Reasoning model** (OpenAI/Gemini) for: refactor, complex generation

    The response contains raw code (markdown fences stripped) ready to inject
    into the Monaco editor.
    """
    request_id = str(uuid.uuid4())
    logger.info(
        "Generate request | id=%s | language=%s | task_type=%s",
        request_id, request.language, request.task_type
    )

    try:
        # Build prompt from template manager
        system_prompt, user_message = get_generation_prompt(
            task_type=request.task_type,
            language=request.language,
            prompt=request.prompt,
            code_context=request.code_context or "",
        )

        # Route to appropriate LLM
        llm_response = await task_router.route(
            task_type=request.task_type,
            system_prompt=system_prompt,
            user_message=user_message,
            endpoint="generate",
        )

    except RuntimeError as e:
        logger.error("All providers failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service Unavailable",
                "detail": "All LLM providers are currently unavailable. Please try again later.",
                "code": "LLM_UNAVAILABLE",
            },
        )
    except httpx.TimeoutException as e:
        logger.error("LLM timeout: %s", e)
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Gateway Timeout",
                "detail": "The LLM provider timed out. Please try again.",
                "code": "LLM_TIMEOUT",
            },
        )
    except httpx.HTTPStatusError as e:
        logger.error("LLM provider HTTP error: %s", e)
        status_code = 502 if e.response.status_code >= 500 else 400
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": "Bad Gateway",
                "detail": f"LLM provider returned an error: {e.response.status_code}",
                "code": "LLM_PROVIDER_ERROR",
            },
        )

    # Strip markdown fences from generated code
    raw_code = strip_markdown_fences(llm_response.content)

    # Extract explanation if the model provided one after the code
    explanation = ""
    content_parts = llm_response.content.split("```")
    if len(content_parts) > 2:
        explanation = content_parts[-1].strip()

    # Build response payload
    response_payload = {
        "code": raw_code,
        "explanation": explanation,
        "routed_model": f"{llm_response.provider}/{llm_response.model}",
        "request_id": request_id,
    }

    # Persist to database
    history_record = RequestHistory(
        id=request_id,
        endpoint_used="generate",
        language=request.language,
        task_type=request.task_type,
        user_input=request.prompt,
        model_routed_to=f"{llm_response.provider}/{llm_response.model}",
        response_payload=response_payload,
        created_at=datetime.now(timezone.utc),
    )
    db.add(history_record)
    await db.commit()

    logger.info("Generate complete | id=%s | model=%s/%s", request_id, llm_response.provider, llm_response.model)

    return GenerateResponse(
        code=raw_code,
        explanation=explanation,
        routed_model=f"{llm_response.provider}/{llm_response.model}",
        request_id=request_id,
    )
