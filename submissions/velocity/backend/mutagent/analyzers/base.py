"""
BaseAnalyzer — the abstract contract every analyzer must implement.

Design rules:
  - Each analyzer has exactly one responsibility.
  - Analyzers NEVER write to the database.
  - Analyzers NEVER import from other analyzers.
  - Analyzers ONLY read from and write to InvestigationContext.
  - Every analyzer returns an AnalyzerResult (never plain booleans or dicts).
  - Every analyzer must handle its own internal exceptions gracefully.

To add a new analyzer:
    class MalwareAnalyzer(BaseAnalyzer):
        name = "MalwareAnalyzer"
        display_name = "Malware Agent"
        timeout_seconds = 3.0

        def run(self, context: InvestigationContext) -> AnalyzerResult:
            ...

Then drop the file in mutagent/analyzers/ — the engine discovers it automatically.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from mutagent.models import (
    AnalyzerResult,
    AnalyzerStatus,
    Evidence,
)
from schemas.detection import DetectionResult, Match, Recommendation, Severity

if TYPE_CHECKING:
    from mutagent.models import InvestigationContext


class BaseAnalyzer(ABC):
    """Abstract base class for all Mutagent analyzers."""

    #: Internal name used as dictionary key, class identifier, and DB field.
    name: str = ""

    #: Human-readable label shown in the dashboard (e.g. "PII Agent").
    display_name: str = ""

    #: Per-analyzer timeout in seconds. The workflow enforces this via
    #: ThreadPoolExecutor.submit().result(timeout=...).
    timeout_seconds: float = 2.0

    @abstractmethod
    def run(self, context: "InvestigationContext") -> AnalyzerResult:
        """
        Execute this analyzer's detection logic against the context.

        Must return an AnalyzerResult. Must not raise — catch all internal
        exceptions and return a FAILED result instead.
        """
        ...

    # ------------------------------------------------------------------
    # Protected helpers available to all analyzers
    # ------------------------------------------------------------------

    def _start_timer(self) -> float:
        """Return the current monotonic time to start measuring execution."""
        return time.monotonic()

    def _elapsed_ms(self, start: float) -> float:
        """Return elapsed milliseconds since start."""
        return round((time.monotonic() - start) * 1000, 2)

    def _success(
        self,
        findings: list[DetectionResult],
        evidence: list[Evidence],
        execution_time_ms: float,
        *,
        summary: str = "",
        extra: dict | None = None,
    ) -> AnalyzerResult:
        """Build a SUCCESS AnalyzerResult from detection outputs."""
        from schemas.detection import SEVERITY_RANK
        severity = Severity.NONE
        recommendation = Recommendation.ALLOW
        total_confidence = 0.0

        for f in findings:
            if SEVERITY_RANK[f.severity] > SEVERITY_RANK[severity]:
                severity = f.severity
            if f.recommendation != Recommendation.ALLOW:
                if SEVERITY_RANK.get(f.severity, 0) > SEVERITY_RANK.get(severity, 0) or recommendation == Recommendation.ALLOW:
                    recommendation = f.recommendation
            if f.score > 0:
                total_confidence += min(f.score / 100, 1.0)

        confidence = round(min(total_confidence, 1.0), 3)

        # Derive recommendation from highest severity if not set
        if not findings:
            recommendation = Recommendation.ALLOW
        else:
            from ai.decision_engine import _DEFAULT_ACTION_BY_SEVERITY
            recommendation = _DEFAULT_ACTION_BY_SEVERITY.get(severity, Recommendation.ALLOW)
            for f in findings:
                if f.recommendation == Recommendation.BLOCK:
                    recommendation = Recommendation.BLOCK
                    break

        if not summary:
            if not findings or severity == Severity.NONE:
                summary = f"{self.display_name}: No issues found."
            else:
                summary = (
                    f"{self.display_name}: Found {len(evidence)} evidence item(s), "
                    f"severity={severity.value}."
                )

        return AnalyzerResult(
            agent_name=self.name,
            display_name=self.display_name,
            status=AnalyzerStatus.SUCCESS,
            execution_time_ms=execution_time_ms,
            confidence=confidence,
            severity=severity,
            findings=findings,
            evidence=evidence,
            recommendation=recommendation,
            summary=summary,
            extra=extra or {},
        )

    def _failed(self, error: str, execution_time_ms: float) -> AnalyzerResult:
        """Build a FAILED AnalyzerResult. Investigation continues."""
        return AnalyzerResult(
            agent_name=self.name,
            display_name=self.display_name,
            status=AnalyzerStatus.FAILED,
            execution_time_ms=execution_time_ms,
            confidence=0.0,
            severity=Severity.NONE,
            findings=[],
            evidence=[],
            recommendation=Recommendation.ALLOW,
            summary=f"{self.display_name} failed: {error}",
            error=error,
        )

    def _skipped(self, reason: str) -> AnalyzerResult:
        """Build a SKIPPED AnalyzerResult for disabled analyzers."""
        return AnalyzerResult(
            agent_name=self.name,
            display_name=self.display_name,
            status=AnalyzerStatus.SKIPPED,
            execution_time_ms=0.0,
            confidence=0.0,
            severity=Severity.NONE,
            findings=[],
            evidence=[],
            recommendation=Recommendation.ALLOW,
            summary=f"{self.display_name} skipped: {reason}",
        )

    def _make_evidence_from_results(
        self,
        results: list[DetectionResult],
        location: str,
    ) -> list[Evidence]:
        """
        Convert a list of DetectionResult objects into structured Evidence items.
        This is the bridge between the existing detector schema and the new
        enterprise evidence layer.
        """
        evidence: list[Evidence] = []
        for result in results:
            if result.severity == Severity.NONE and not result.matches:
                continue
            if result.matches:
                for match in result.matches:
                    evidence.append(
                        Evidence(
                            label=match.label,
                            value_preview=match.value_preview,
                            confidence=min(result.score / 100, 1.0),
                            location=location,
                            detector=result.detector,
                            severity=result.severity,
                            start=match.start,
                            end=match.end,
                        )
                    )
            else:
                # No span matches but still a finding — create a summary evidence
                evidence.append(
                    Evidence(
                        label=result.detector.upper(),
                        value_preview=result.reason[:80],
                        confidence=min(result.score / 100, 1.0),
                        location=location,
                        detector=result.detector,
                        severity=result.severity,
                    )
                )
        return evidence

    def _neutral_detection_result(self, detector: str, reason: str) -> DetectionResult:
        """Produce a clean no-finding DetectionResult."""
        return DetectionResult(
            detector=detector,
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason=reason,
        )
