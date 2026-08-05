"""
Investigations API — read-only endpoints for the Security Investigation
dashboard page.

All endpoints require admin or security_analyst role.

Routes:
    GET /api/investigations                    paginated list
    GET /api/investigations/{scan_id}          full trace (summary + agents + timeline)
    GET /api/investigations/{scan_id}/timeline timeline events only
    GET /api/investigations/{scan_id}/agents   per-analyzer results + evidence
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth.dependencies import require_analyst_or_admin
from database import get_db
from models.investigation import AgentExecution, Investigation, TimelineEvent
from models.user import User
from schemas.investigations import (
    AgentExecutionSchema,
    EvidenceSchema,
    InvestigationDetail,
    InvestigationListItem,
    InvestigationListResponse,
    TimelineEventSchema,
)

router = APIRouter(prefix="/api/investigations", tags=["Investigations"])


@router.get("", response_model=InvestigationListResponse)
def list_investigations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    decision: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_analyst_or_admin),
):
    """Paginated list of investigations with optional decision/severity filters."""
    query = select(Investigation, User).outerjoin(User, Investigation.user_id == User.id)
    count_query = select(func.count()).select_from(Investigation)

    if decision:
        query = query.where(Investigation.decision == decision.upper())
        count_query = count_query.where(Investigation.decision == decision.upper())
    if severity:
        query = query.where(Investigation.overall_severity == severity.upper())
        count_query = count_query.where(Investigation.overall_severity == severity.upper())

    total = db.scalar(count_query) or 0
    query = (
        query
        .order_by(Investigation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    results = db.execute(query).all()

    items = [
        InvestigationListItem(
            id=inv.id,
            user_id=inv.user_id,
            user_email=usr.email if usr else None,
            user_name=usr.full_name if usr else None,
            user_department=usr.department if usr else None,
            target_ai=inv.target_ai,
            file_count=inv.file_count,
            total_analyzers=inv.total_analyzers,
            analyzers_succeeded=inv.analyzers_succeeded,
            analyzers_failed=inv.analyzers_failed,
            analyzers_skipped=inv.analyzers_skipped,
            overall_score=inv.overall_score,
            overall_severity=inv.overall_severity,
            decision=inv.decision,
            total_execution_ms=inv.total_execution_ms,
            created_at=inv.created_at,
        )
        for inv, usr in results
    ]

    total_pages = max(1, (total + page_size - 1) // page_size)
    return InvestigationListResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@router.get("/{scan_id}", response_model=InvestigationDetail)
def get_investigation(
    scan_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_analyst_or_admin),
):
    """Full investigation trace — summary, agent executions, timeline."""
    inv_user = db.execute(
        select(Investigation, User)
        .outerjoin(User, Investigation.user_id == User.id)
        .where(Investigation.id == scan_id)
    ).first()

    if inv_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

    inv, usr = inv_user

    agents = db.scalars(
        select(AgentExecution)
        .where(AgentExecution.investigation_id == scan_id)
        .order_by(AgentExecution.created_at)
    ).all()

    timeline = db.scalars(
        select(TimelineEvent)
        .where(TimelineEvent.investigation_id == scan_id)
        .order_by(TimelineEvent.timestamp)
    ).all()

    return InvestigationDetail(
        id=inv.id,
        user_id=inv.user_id,
        user_email=usr.email if usr else None,
        user_name=usr.full_name if usr else None,
        user_department=usr.department if usr else None,
        target_ai=inv.target_ai,
        prompt_length=inv.prompt_length,
        file_count=inv.file_count,
        total_analyzers=inv.total_analyzers,
        analyzers_succeeded=inv.analyzers_succeeded,
        analyzers_failed=inv.analyzers_failed,
        analyzers_skipped=inv.analyzers_skipped,
        overall_score=inv.overall_score,
        overall_severity=inv.overall_severity,
        decision=inv.decision,
        total_execution_ms=inv.total_execution_ms,
        summary=inv.summary or {},
        created_at=inv.created_at,
        agent_executions=[
            AgentExecutionSchema(
                id=a.id,
                agent_name=a.agent_name,
                display_name=a.display_name,
                status=a.status,
                execution_time_ms=a.execution_time_ms,
                confidence=a.confidence,
                severity=a.severity,
                recommendation=a.recommendation,
                summary=a.summary,
                error=a.error,
                findings=a.findings or [],
                evidence=[EvidenceSchema(**ev) for ev in (a.evidence or [])],
                created_at=a.created_at,
            )
            for a in agents
        ],
        timeline=[
            TimelineEventSchema(
                id=e.id,
                event_type=e.event_type,
                analyzer_name=e.analyzer_name,
                message=e.message,
                timestamp=e.timestamp,
                duration_ms=e.duration_ms,
                metadata=e.event_metadata or {},
            )
            for e in timeline
        ],
    )


@router.get("/{scan_id}/timeline", response_model=list[TimelineEventSchema])
def get_investigation_timeline(
    scan_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_analyst_or_admin),
):
    """Timeline events only — lightweight endpoint for the timeline panel."""
    _assert_exists(db, scan_id)
    events = db.scalars(
        select(TimelineEvent)
        .where(TimelineEvent.investigation_id == scan_id)
        .order_by(TimelineEvent.timestamp)
    ).all()
    return [_timeline_to_schema(e) for e in events]


@router.get("/{scan_id}/agents", response_model=list[AgentExecutionSchema])
def get_investigation_agents(
    scan_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_analyst_or_admin),
):
    """Per-analyzer results with full evidence — for the Evidence panel."""
    _assert_exists(db, scan_id)
    agents = db.scalars(
        select(AgentExecution)
        .where(AgentExecution.investigation_id == scan_id)
        .order_by(AgentExecution.created_at)
    ).all()
    return [_agent_to_schema(a) for a in agents]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_exists(db: Session, scan_id: str) -> None:
    if not db.get(Investigation, scan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")


def _agent_to_schema(agent: AgentExecution) -> AgentExecutionSchema:
    evidence = [
        EvidenceSchema(**e) if isinstance(e, dict) else EvidenceSchema(**e)
        for e in (agent.evidence or [])
    ]
    return AgentExecutionSchema(
        id=agent.id,
        agent_name=agent.agent_name,
        display_name=agent.display_name,
        status=agent.status,
        execution_time_ms=agent.execution_time_ms,
        confidence=agent.confidence,
        severity=agent.severity,
        recommendation=agent.recommendation,
        summary=agent.summary,
        error=agent.error,
        findings=agent.findings or [],
        evidence=evidence,
        created_at=agent.created_at,
    )


def _timeline_to_schema(event: TimelineEvent) -> TimelineEventSchema:
    return TimelineEventSchema(
        id=event.id,
        event_type=event.event_type,
        analyzer_name=event.analyzer_name,
        message=event.message,
        timestamp=event.timestamp,
        duration_ms=event.duration_ms,
        metadata=event.event_metadata or {},
    )
