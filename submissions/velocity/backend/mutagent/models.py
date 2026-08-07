"""
Mutagent Data Models — all shared dataclasses and Pydantic models used
throughout the multi-analyzer investigation engine.

Nothing in this module performs detection or touches the database; it only
defines the data shapes that flow between components.

Key types:
    InvestigationContext — the single shared object passed to every analyzer
    AnalyzerResult       — standard output every analyzer returns
    Evidence             — structured, enterprise-grade evidence item
    TimelineEvent        — timestamped record of investigation progress
    AnalyzerStatus       — lifecycle state of one analyzer run
    TimelineEventType    — what kind of event occurred in the timeline
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

from schemas.detection import DetectionResult, Recommendation, Severity
from schemas.scan import FileFindingSummary, ScanFileInput

if TYPE_CHECKING:
    from models.policy import Policy
    from models.settings import OrgSettings
    from models.user import User
    from ai.decision_engine import Decision


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AnalyzerStatus(str, Enum):
    """Lifecycle state of a single analyzer run."""
    PENDING   = "PENDING"
    RUNNING   = "RUNNING"
    SUCCESS   = "SUCCESS"
    FAILED    = "FAILED"
    SKIPPED   = "SKIPPED"
    TIMEOUT   = "TIMEOUT"


class TimelineEventType(str, Enum):
    """All possible events that can appear in an investigation timeline."""
    ANALYZER_STARTED   = "analyzer_started"
    ANALYZER_FINISHED  = "analyzer_finished"
    ANALYZER_FAILED    = "analyzer_failed"
    ANALYZER_SKIPPED   = "analyzer_skipped"
    ANALYZER_TIMEOUT   = "analyzer_timeout"
    ANALYZER_RECOVERED = "analyzer_recovered"
    DECISION_MADE      = "decision_made"
    INVESTIGATION_START = "investigation_start"
    INVESTIGATION_END   = "investigation_end"


# ---------------------------------------------------------------------------
# Evidence — the star of enterprise explainability
# ---------------------------------------------------------------------------

@dataclass
class Evidence:
    """
    Structured, human-readable evidence item produced by an analyzer.

    This is what enterprises love: instead of just knowing *that* PII was
    found, an admin can see *exactly* what was found, where, by which
    detector, with what confidence.

    Fields:
        label         — e.g. "EMAIL", "AWS_ACCESS_KEY", "JAILBREAK_ATTEMPT"
        value_preview — masked/previewed value (never the raw secret)
        confidence    — 0.0–1.0, how certain the detector is
        location      — "prompt" | "file:<filename>"
        detector      — which underlying detector produced this (e.g. "presidio")
        severity      — severity level of this specific finding
        start         — character offset in the source text (if available)
        end           — end offset (if available)
        metadata      — any extra context the analyzer wants to attach
    """
    label: str
    value_preview: str
    confidence: float
    location: str
    detector: str
    severity: Severity
    start: int | None = None
    end: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "value_preview": self.value_preview,
            "confidence": self.confidence,
            "location": self.location,
            "detector": self.detector,
            "severity": self.severity.value,
            "start": self.start,
            "end": self.end,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Analyzer Result
# ---------------------------------------------------------------------------

@dataclass
class AnalyzerResult:
    """
    Standard output shape that every Analyzer must return.

    Internally the class is named *Analyzer (e.g. PiiAnalyzer); the
    display_name is the UI-facing label (e.g. "PII Agent").
    """
    agent_name: str           # internal class name, e.g. "PiiAnalyzer"
    display_name: str         # UI label, e.g. "PII Agent"
    status: AnalyzerStatus
    execution_time_ms: float
    confidence: float         # 0.0–1.0
    severity: Severity
    findings: list[DetectionResult]
    evidence: list[Evidence]  # structured, enterprise-grade evidence
    recommendation: Recommendation
    summary: str              # one-sentence human-readable summary
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)  # analyzer-specific payload

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "display_name": self.display_name,
            "status": self.status.value,
            "execution_time_ms": self.execution_time_ms,
            "confidence": self.confidence,
            "severity": self.severity.value,
            "findings": [
                {
                    "detector": f.detector,
                    "severity": f.severity.value,
                    "score": f.score,
                    "reason": f.reason,
                    "matches": [m.model_dump() for m in f.matches],
                }
                for f in self.findings
            ],
            "evidence": [e.to_dict() for e in self.evidence],
            "recommendation": self.recommendation.value,
            "summary": self.summary,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Timeline Event
# ---------------------------------------------------------------------------

@dataclass
class TimelineEvent:
    """
    A single timestamped event in the investigation timeline.

    Richer than started/finished — also captures skipped, timeout,
    recovered, and decision events so traces tell a complete story.
    """
    event_type: TimelineEventType
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    analyzer_name: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "analyzer_name": self.analyzer_name,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Investigation Context — the shared state object
# ---------------------------------------------------------------------------

@dataclass
class InvestigationContext:
    """
    The single shared state object that flows through the entire
    investigation. Every analyzer receives it, reads from it, and writes
    its outputs back to it.

    Nothing is stored in globals. Everything flows through this object.

    Fields set at construction (by mutagent/context.py):
        scan_id, user, browser, raw_prompt, uploaded_files, keywords,
        policies, org_settings, risk_weights, enabled_analyzers

    Fields populated during investigation (by analyzers):
        prompt (normalized), findings, file_findings, timeline,
        analyzer_results, risk_score, decision, sanitized_prompt,
        execution_times
    """
    # --- Set at construction ---
    scan_id: str
    user: Any                              # models.user.User
    browser: str                           # target AI, e.g. "ChatGPT"
    raw_prompt: str                        # original, pre-normalization
    uploaded_files: list[ScanFileInput]
    keywords: list[str]
    policies: list[Any]                    # list[models.policy.Policy]
    org_settings: Any                      # models.settings.OrgSettings
    risk_weights: dict[str, float]
    enabled_analyzers: set[str]            # empty set = all enabled

    # --- Populated during investigation ---
    prompt: str = ""                       # set by ContextAnalyzer (normalized)
    findings: list[DetectionResult] = field(default_factory=list)
    file_findings: list[FileFindingSummary] = field(default_factory=list)
    timeline: list[TimelineEvent] = field(default_factory=list)
    analyzer_results: dict[str, AnalyzerResult] = field(default_factory=dict)
    risk_score: int = 0
    decision: Any = None                   # ai.decision_engine.Decision | None
    sanitized_prompt: str = ""
    execution_times: dict[str, float] = field(default_factory=dict)

    def is_analyzer_enabled(self, analyzer_name: str) -> bool:
        """Return True if the analyzer should run (empty set = all enabled)."""
        if not self.enabled_analyzers:
            return True
        return analyzer_name in self.enabled_analyzers

    def add_findings(self, results: list[DetectionResult]) -> None:
        """Thread-safe append (GIL protects list.extend in CPython)."""
        self.findings.extend(results)

    def record_analyzer_result(self, result: AnalyzerResult) -> None:
        self.analyzer_results[result.agent_name] = result
        self.execution_times[result.agent_name] = result.execution_time_ms


# ---------------------------------------------------------------------------
# Default risk weights
# ---------------------------------------------------------------------------

# FileIntelAnalyzer is weighted 1.0 (not dampened) because its CRITICAL-tier
# identity findings (ai/file_risk.py - e.g. a bare .env or id_rsa upload,
# score=80) are deliberately scored high enough to cross the Risk Engine's
# CRITICAL threshold (>=75) "on their own, with no other detector needing to
# corroborate them" (see ai/file_risk.py's module docstring - a bare .env
# upload is documented to BLOCK by default even with empty/unreadable
# content). Any weight below ~0.94 here silently drags that score under the
# CRITICAL cutoff, downgrading the decision to REDACT and contradicting that
# documented behavior - not a detection gap, just a fusion weight that has
# to stay 1.0 for identity-risk scores tuned assuming no dilution.
DEFAULT_RISK_WEIGHTS: dict[str, float] = {
    "PiiAnalyzer":        0.6,
    "SecretsAnalyzer":    1.0,
    "InjectionAnalyzer":  1.0,
    "ComplianceAnalyzer": 0.8,
    "FileIntelAnalyzer":  1.0,
}

DEFAULT_ANALYZER_TIMEOUT_SECONDS: float = 2.0
