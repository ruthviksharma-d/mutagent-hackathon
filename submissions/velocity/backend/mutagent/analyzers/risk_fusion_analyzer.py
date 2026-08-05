"""
RiskFusionAnalyzer — Stage 4: aggregates findings from all analyzers into
one weighted overall risk score.

Unlike the old risk_engine.py (simple sum of scores), this analyzer applies
configurable per-analyzer weights from context.risk_weights, which are stored
in OrgSettings and tunable by admins from the dashboard.

Default weights (if not configured):
    SecretsAnalyzer:    1.0  (highest — live credentials are critical)
    InjectionAnalyzer:  1.0  (jailbreaks / injections are critical)
    ComplianceAnalyzer: 0.8  (policy violations are severe)
    FileIntelAnalyzer:  0.7  (identity risk matters)
    PiiAnalyzer:        0.6  (important but slightly lower default weight)

Admins can tune these from Settings → Risk Weights.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mutagent.analyzers.base import BaseAnalyzer
from mutagent.models import AnalyzerStatus, Evidence

if TYPE_CHECKING:
    from mutagent.models import AnalyzerResult, InvestigationContext

logger = logging.getLogger("promptshield.mutagent.risk_fusion_analyzer")


class RiskFusionAnalyzer(BaseAnalyzer):
    """
    Risk Fusion — weighted aggregation of all analyzer outputs.

    Receives the full InvestigationContext with all prior findings and
    analyzer results. Produces the overall risk score, severity, and
    confidence that DecisionAnalyzer will use.
    """
    name = "RiskFusionAnalyzer"
    display_name = "Risk Fusion Agent"
    timeout_seconds = 1.0

    def run(self, context: "InvestigationContext") -> "AnalyzerResult":
        start = self._start_timer()
        try:
            from schemas.detection import SEVERITY_RANK, Recommendation, Severity

            # Collect per-analyzer weighted contributions
            weighted_total = 0.0
            contributions: list[dict] = []

            for analyzer_name, result in context.analyzer_results.items():
                if result.status not in (AnalyzerStatus.SUCCESS,):
                    continue
                # Skip non-detection analyzers
                if analyzer_name in ("ContextAnalyzer", "RiskFusionAnalyzer", "DecisionAnalyzer"):
                    continue

                weight = context.risk_weights.get(analyzer_name, 0.5)
                raw_score = sum(f.score for f in result.findings)
                weighted_contribution = raw_score * weight
                weighted_total += weighted_contribution

                if raw_score > 0:
                    contributions.append({
                        "analyzer": getattr(result, "display_name", getattr(result, "agent_name", analyzer_name)),
                        "raw_score": raw_score,
                        "weight": weight,
                        "contribution": round(weighted_contribution, 2),
                    })

            overall_score = min(int(weighted_total), 100)
            context.risk_score = overall_score

            # Severity from score
            if overall_score >= 75:
                severity = Severity.CRITICAL
            elif overall_score >= 50:
                severity = Severity.HIGH
            elif overall_score >= 25:
                severity = Severity.MEDIUM
            elif overall_score > 0:
                severity = Severity.LOW
            else:
                severity = Severity.NONE

            # Confidence: fraction of enabled (non-skipped) analyzers that contributed
            enabled_results = [
                r for name, r in context.analyzer_results.items()
                if r.status == AnalyzerStatus.SUCCESS
                and name not in ("ContextAnalyzer", "RiskFusionAnalyzer", "DecisionAnalyzer")
            ]
            contributing = [r for r in enabled_results if any(f.score > 0 for f in r.findings)]
            confidence = round(len(contributing) / max(len(enabled_results), 1), 3)

            # Build evidence showing the weighted breakdown
            evidence: list[Evidence] = []
            for c in sorted(contributions, key=lambda x: x["contribution"], reverse=True):
                evidence.append(Evidence(
                    label="RISK_CONTRIBUTION",
                    value_preview=(
                        f"{c['analyzer']}: raw={c['raw_score']} × weight={c['weight']:.1f} "
                        f"= {c['contribution']:.1f}"
                    ),
                    confidence=confidence,
                    location="risk_engine",
                    detector="risk_fusion",
                    severity=severity,
                    metadata=c,
                ))

            # Top contributing detectors for summary
            top_analyzers = [c["analyzer"] for c in contributions[:3]]
            if top_analyzers:
                summary = (
                    f"Weighted risk score: {overall_score}/100 (severity={severity.value}). "
                    f"Top contributors: {', '.join(top_analyzers)}."
                )
            else:
                summary = f"Risk score: {overall_score}/100 — no significant findings."

            elapsed = self._elapsed_ms(start)

            # Create a synthetic finding to carry the overall risk info
            from schemas.detection import DetectionResult, Recommendation
            risk_finding = DetectionResult(
                detector="risk_fusion",
                severity=severity,
                score=overall_score,
                matches=[],
                recommendation=Recommendation.ALLOW,  # DecisionAnalyzer handles action
                reason=summary,
            )

            result = self._success(
                [risk_finding],
                evidence,
                elapsed,
                summary=summary,
                extra={
                    "overall_score": overall_score,
                    "overall_severity": severity.value,
                    "confidence": confidence,
                    "contributions": contributions,
                    "risk_weights_used": dict(context.risk_weights),
                },
            )
            # Override severity to the computed one
            result.severity = severity
            return result

        except Exception as exc:
            logger.exception("RiskFusionAnalyzer failed")
            return self._failed(str(exc), self._elapsed_ms(start))
