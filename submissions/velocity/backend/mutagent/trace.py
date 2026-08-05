"""
Trace helpers — timeline recording, JSON investigation summary generation,
and DB persistence.

Every scan automatically generates a structured trace. The summary is JSON
(not plain text) so the dashboard can render it dynamically, and
human-readable text can be generated from it on demand.

Timeline event types (rich — not just started/finished):
    investigation_start    investigation_end
    analyzer_started       analyzer_finished
    analyzer_failed        analyzer_skipped
    analyzer_timeout       analyzer_recovered
    decision_made
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from mutagent.models import (
    AnalyzerResult,
    AnalyzerStatus,
    InvestigationContext,
    TimelineEvent,
    TimelineEventType,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger("promptshield.mutagent.trace")


# ---------------------------------------------------------------------------
# Timeline recording helpers
# ---------------------------------------------------------------------------

def record_investigation_start(ctx: InvestigationContext) -> None:
    ctx.timeline.append(TimelineEvent(
        event_type=TimelineEventType.INVESTIGATION_START,
        message=f"Investigation started for user {ctx.user.email} on {ctx.browser}",
        metadata={"scan_id": ctx.scan_id, "file_count": len(ctx.uploaded_files)},
    ))


def record_investigation_end(ctx: InvestigationContext, total_ms: float) -> None:
    decision_str = ctx.decision.action.value if ctx.decision else "UNKNOWN"
    ctx.timeline.append(TimelineEvent(
        event_type=TimelineEventType.INVESTIGATION_END,
        message=f"Investigation complete — decision: {decision_str}",
        duration_ms=total_ms,
        metadata={"risk_score": ctx.risk_score, "decision": decision_str},
    ))


def record_start(ctx: InvestigationContext, analyzer_name: str) -> None:
    ctx.timeline.append(TimelineEvent(
        event_type=TimelineEventType.ANALYZER_STARTED,
        analyzer_name=analyzer_name,
        message=f"{analyzer_name} started",
    ))


def record_finish(
    ctx: InvestigationContext,
    analyzer_name: str,
    result: AnalyzerResult,
) -> None:
    if result.status == AnalyzerStatus.FAILED:
        ctx.timeline.append(TimelineEvent(
            event_type=TimelineEventType.ANALYZER_FAILED,
            analyzer_name=analyzer_name,
            message=f"{analyzer_name} failed: {result.error}",
            duration_ms=result.execution_time_ms,
            metadata={"error": result.error},
        ))
    elif result.status == AnalyzerStatus.TIMEOUT:
        ctx.timeline.append(TimelineEvent(
            event_type=TimelineEventType.ANALYZER_TIMEOUT,
            analyzer_name=analyzer_name,
            message=f"{analyzer_name} timed out after {result.execution_time_ms:.0f}ms",
            duration_ms=result.execution_time_ms,
        ))
    else:
        ctx.timeline.append(TimelineEvent(
            event_type=TimelineEventType.ANALYZER_FINISHED,
            analyzer_name=analyzer_name,
            message=(
                f"{analyzer_name} finished — "
                f"severity={result.severity.value}, "
                f"evidence={len(result.evidence)}, "
                f"time={result.execution_time_ms:.0f}ms"
            ),
            duration_ms=result.execution_time_ms,
            metadata={
                "severity": result.severity.value,
                "evidence_count": len(result.evidence),
                "confidence": result.confidence,
            },
        ))


def record_skipped(
    ctx: InvestigationContext,
    analyzer_name: str,
    reason: str,
) -> None:
    ctx.timeline.append(TimelineEvent(
        event_type=TimelineEventType.ANALYZER_SKIPPED,
        analyzer_name=analyzer_name,
        message=f"{analyzer_name} skipped: {reason}",
        metadata={"reason": reason},
    ))


def record_recovered(ctx: InvestigationContext, analyzer_name: str) -> None:
    ctx.timeline.append(TimelineEvent(
        event_type=TimelineEventType.ANALYZER_RECOVERED,
        analyzer_name=analyzer_name,
        message=f"{analyzer_name} recovered from error — investigation continues with reduced confidence",
    ))


def record_decision(ctx: InvestigationContext) -> None:
    if ctx.decision:
        ctx.timeline.append(TimelineEvent(
            event_type=TimelineEventType.DECISION_MADE,
            message=f"Final decision: {ctx.decision.action.value} (score={ctx.decision.score}, risk={ctx.decision.risk.value})",
            metadata={
                "action": ctx.decision.action.value,
                "risk": ctx.decision.risk.value,
                "score": ctx.decision.score,
                "reason": ctx.decision.reason,
            },
        ))


# ---------------------------------------------------------------------------
# JSON investigation summary (machine-readable, dashboard-renderable)
# ---------------------------------------------------------------------------

def build_investigation_summary(ctx: InvestigationContext) -> dict:
    """
    Build a structured JSON summary of the investigation.

    This is the single source of truth for the dashboard's Investigation
    Detail page. Human-readable text is generated FROM this structure,
    not stored separately.
    """
    all_evidence = [
        e.to_dict()
        for r in ctx.analyzer_results.values()
        for e in r.evidence
    ]

    top_findings = _top_findings(ctx)
    overall_confidence = _overall_confidence(ctx)
    total_ms = sum(ctx.execution_times.values())

    analyzers_summary = []
    for name, result in ctx.analyzer_results.items():
        analyzers_summary.append({
            "name": result.display_name,
            "internal_name": result.agent_name,
            "status": result.status.value,
            "severity": result.severity.value,
            "confidence": result.confidence,
            "findings_count": len(result.findings),
            "evidence_count": len(result.evidence),
            "execution_time_ms": result.execution_time_ms,
            "recommendation": result.recommendation.value,
            "summary": result.summary,
            "error": result.error,
        })

    return {
        "scan_id": ctx.scan_id,
        "user": {
            "id": ctx.user.id,
            "email": ctx.user.email,
            "name": getattr(ctx.user, "full_name", ctx.user.email),
        },
        "target_ai": ctx.browser,
        "file_count": len(ctx.uploaded_files),
        "risk_score": ctx.risk_score,
        "decision": ctx.decision.action.value if ctx.decision else "UNKNOWN",
        "risk_level": ctx.decision.risk.value if ctx.decision else "NONE",
        "overall_confidence": overall_confidence,
        "reasoning": ctx.decision.reason if ctx.decision else "",
        "analyzers": analyzers_summary,
        "evidence": all_evidence,
        "top_findings": top_findings,
        "timeline_events": len(ctx.timeline),
        "total_execution_ms": round(total_ms, 2),
        "file_findings": [f.model_dump() for f in ctx.file_findings],
    }


def _overall_confidence(ctx: InvestigationContext) -> float:
    """Average confidence across all succeeded analyzers."""
    succeeded = [
        r for r in ctx.analyzer_results.values()
        if r.status == AnalyzerStatus.SUCCESS
    ]
    if not succeeded:
        return 0.0
    return round(sum(r.confidence for r in succeeded) / len(succeeded), 3)


def _top_findings(ctx: InvestigationContext, limit: int = 5) -> list[dict]:
    """Return the top N most severe findings across all analyzers."""
    from schemas.detection import SEVERITY_RANK
    all_findings = [f for r in ctx.analyzer_results.values() for f in r.findings]
    sorted_findings = sorted(all_findings, key=lambda f: (SEVERITY_RANK[f.severity], f.score), reverse=True)
    return [
        {
            "detector": f.detector,
            "severity": f.severity.value,
            "score": f.score,
            "reason": f.reason,
        }
        for f in sorted_findings[:limit]
    ]


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------

def persist_trace(
    db: "Session",
    ctx: InvestigationContext,
    summary: dict,
) -> None:
    """
    Persist the investigation trace to the database.
    Writes to: investigations, agent_executions, timeline_events.
    Never raises — a trace write failure must not fail the scan.
    """
    try:
        from models.investigation import AgentExecution, Investigation, TimelineEvent as DBTimelineEvent
        total_ms = sum(ctx.execution_times.values())
        succeeded = sum(1 for r in ctx.analyzer_results.values() if r.status == AnalyzerStatus.SUCCESS)
        failed = sum(1 for r in ctx.analyzer_results.values() if r.status in (AnalyzerStatus.FAILED, AnalyzerStatus.TIMEOUT))
        skipped = sum(1 for r in ctx.analyzer_results.values() if r.status == AnalyzerStatus.SKIPPED)

        investigation = Investigation(
            id=ctx.scan_id,
            user_id=ctx.user.id,
            target_ai=ctx.browser,
            prompt_length=len(ctx.prompt),
            file_count=len(ctx.uploaded_files),
            total_analyzers=len(ctx.analyzer_results),
            analyzers_succeeded=succeeded,
            analyzers_failed=failed,
            analyzers_skipped=skipped,
            overall_score=ctx.risk_score,
            overall_severity=ctx.decision.risk.value if ctx.decision else "NONE",
            decision=ctx.decision.action.value if ctx.decision else "UNKNOWN",
            total_execution_ms=round(total_ms, 2),
            summary=summary,
        )
        db.add(investigation)
        db.flush()

        for name, result in ctx.analyzer_results.items():
            exec_row = AgentExecution(
                investigation_id=ctx.scan_id,
                agent_name=result.agent_name,
                display_name=result.display_name,
                status=result.status.value,
                execution_time_ms=result.execution_time_ms,
                confidence=result.confidence,
                severity=result.severity.value,
                recommendation=result.recommendation.value,
                summary=result.summary,
                error=result.error,
                findings=[
                    {
                        "detector": f.detector,
                        "severity": f.severity.value,
                        "score": f.score,
                        "reason": f.reason,
                        "matches": [m.model_dump() for m in f.matches],
                    }
                    for f in result.findings
                ],
                evidence=[e.to_dict() for e in result.evidence],
            )
            db.add(exec_row)

        for event in ctx.timeline:
            db.add(DBTimelineEvent(
                investigation_id=ctx.scan_id,
                event_type=event.event_type.value,
                analyzer_name=event.analyzer_name,
                message=event.message,
                timestamp=event.timestamp,
                duration_ms=event.duration_ms,
                event_metadata=event.metadata,
            ))

        db.commit()
        logger.debug("Trace persisted for scan_id=%s", ctx.scan_id)

    except Exception:
        logger.exception(
            "Failed to persist investigation trace for scan_id=%s — "
            "scan result is unaffected.", ctx.scan_id
        )
        try:
            db.rollback()
        except Exception:
            pass
