"""
Policy model - CRUD-managed rules that let admins override the Risk
Engine's default action for a given detector. Loaded fresh from MySQL on
every scan (no caching layer, per project constraints) and evaluated in
priority order by ai/policy_engine.py.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)  # lower = evaluated first

    # Matches a DetectionResult.detector value, or "all" to match any detector.
    detection_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # ALLOW | WARN | REDACT | BLOCK
    action: Mapped[str] = mapped_column(String(20), nullable=False)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
