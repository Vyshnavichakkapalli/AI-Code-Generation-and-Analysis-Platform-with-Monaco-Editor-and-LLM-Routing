"""History API Route.

GET /api/v1/history
- Returns paginated request history sorted by most recent first
- Supports limit/offset query parameters
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.history import RequestHistory
from src.routes.schemas import HistoryResponse, HistoryItem

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/history",
    response_model=list[HistoryItem],
    summary="Retrieve history of all past user requests and system responses",
)
async def get_history(
    limit: int = Query(default=50, ge=1, le=200, description="Number of records to return"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    db: AsyncSession = Depends(get_db),
) -> list[HistoryItem]:
    """
    Return an array of objects representing past requests, sorted most-recent first.
    """
    # Fetch paginated records sorted by most recent first
    result = await db.execute(
        select(RequestHistory)
        .order_by(RequestHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    records = result.scalars().all()

    items = [
        HistoryItem(
            id=r.id,
            endpoint_used=r.endpoint_used,
            language=r.language,
            task_type=r.task_type,
            user_input=r.user_input,
            model_routed_to=r.model_routed_to,
            response_payload=r.response_payload,
            created_at=r.created_at,
        )
        for r in records
    ]

    logger.info("History fetch | count=%d | limit=%d | offset=%d", len(items), limit, offset)

    return items
