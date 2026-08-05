"""
Pydantic response schemas for the investigations API endpoints.

These are read-only schemas — investigations are written by the engine,
never via the API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EvidenceSchema(BaseModel):
    label: str
    value_preview: str
    confidence: float
    location: str
    detector: str
    severity: str
    start: int | None = None
    end: int | None = None
    metadata: dict[str, Any] = {}


class AgentExecutionSchema(BaseModel):
    id: str
    agent_name: str
    display_name: str
    status: str
    execution_time_ms: float
    confidence: float
    severity: str
    recommendation: str
    summary: str
    error: str | None = None
    findings: list[dict] = []
    evidence: list[EvidenceSchema] = []
    created_at: datetime


class TimelineEventSchema(BaseModel):
    id: str
    event_type: str
    analyzer_name: str | None = None
    message: str
    timestamp: datetime
    duration_ms: float | None = None
    metadata: dict[str, Any] = {}


class InvestigationListItem(BaseModel):
    id: str
    user_id: str
    user_email: str | None = None
    user_name: str | None = None
    user_department: str | None = None
    target_ai: str
    file_count: int
    total_analyzers: int
    analyzers_succeeded: int
    analyzers_failed: int
    analyzers_skipped: int
    overall_score: int
    overall_severity: str
    decision: str
    total_execution_ms: float
    created_at: datetime


class InvestigationDetail(BaseModel):
    id: str
    user_id: str
    user_email: str | None = None
    user_name: str | None = None
    user_department: str | None = None
    target_ai: str
    prompt_length: int
    file_count: int
    total_analyzers: int
    analyzers_succeeded: int
    analyzers_failed: int
    analyzers_skipped: int
    overall_score: int
    overall_severity: str
    decision: str
    total_execution_ms: float
    summary: dict[str, Any]
    created_at: datetime
    agent_executions: list[AgentExecutionSchema] = []
    timeline: list[TimelineEventSchema] = []


class InvestigationListResponse(BaseModel):
    items: list[InvestigationListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
