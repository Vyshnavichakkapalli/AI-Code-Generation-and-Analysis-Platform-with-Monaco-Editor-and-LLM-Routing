"""ORM models for database persistence."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class RequestHistory(Base):
    """Stores the full history of every generate and analyze request."""

    __tablename__ = "request_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    endpoint_used: Mapped[str] = mapped_column(String(50), nullable=False)  # 'generate' | 'analyze'
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=True)
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    model_routed_to: Mapped[str] = mapped_column(String(200), nullable=False)
    response_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "endpoint_used": self.endpoint_used,
            "language": self.language,
            "task_type": self.task_type,
            "user_input": self.user_input,
            "model_routed_to": self.model_routed_to,
            "response_payload": self.response_payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
