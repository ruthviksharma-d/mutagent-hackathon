"""
Investigation DB models — 3 new tables that capture the multi-analyzer
investigation trace for every scan.

Tables:
    investigations      — one row per scan (linked to audit_logs by scan_id)
    agent_executions    — one row per analyzer per scan
    timeline_events     — rich timestamped event log per scan

Design notes:
    - No Finding table: findings are stored as JSON in agent_executions.
    - investigations.id = audit_log.id (same UUID) — they are linked.
    - Existing audit_logs table is NOT touched.
    - create_all() on startup creates these if they don't exist.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Investigation(Base):
    """
    One investigation per scan. The id matches the audit_log.id for the
    same scan, allowing JOIN-free cross-reference between the two tables.
    """
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    target_ai: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_analyzers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analyzers_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analyzers_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analyzers_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    overall_severity: Mapped[str] = mapped_column(String(20), nullable=False, default="NONE", index=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False, default="ALLOW", index=True)
    total_execution_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, nullable=False, index=True
    )


class AgentExecution(Base):
    """
    One row per analyzer per investigation. Stores findings and structured
    evidence as JSON — no separate Finding table needed.
    """
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("investigations.id"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="NONE")
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False, default="ALLOW")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, nullable=False
    )


class TimelineEvent(Base):
    """
    Rich timestamped event log for one investigation.

    Event types (richer than just started/finished):
        investigation_start  investigation_end
        analyzer_started     analyzer_finished
        analyzer_failed      analyzer_skipped
        analyzer_timeout     analyzer_recovered
        decision_made
    """
    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("investigations.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    analyzer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
