"""
DecisionAnalyzer — Stage 5 (final): produces the authoritative scan decision.

Reads:
    RiskFusionAnalyzer result → overall risk score and severity
    ComplianceAnalyzer result → policy outcome (policies always win)

Calls:
    ai/decision_engine.py::decide()   — existing decision logic
    ai/redactor.py::redact_text()     — prompt sanitization

Populates:
    context.decision         — the final Decision object
    context.sanitized_prompt — redacted prompt text
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mutagent.analyzers.base import BaseAnalyzer
from mutagent.models import AnalyzerStatus, Evidence

if TYPE_CHECKING:
    from mutagent.models import AnalyzerResult, InvestigationContext

logger = logging.getLogger("promptshield.mutagent.decision_analyzer")


class DecisionAnalyzer(BaseAnalyzer):
    """
    Final decision maker — combines risk assessment with policy outcome.

    Policies always override risk-based defaults (explicit admin intent
    wins over automatic severity mapping), matching the existing engine
    behavior exactly.
    """
    name = "DecisionAnalyzer"
    display_name = "Decision Agent"
    timeout_seconds = 1.0

    def run(self, context: "InvestigationContext") -> "AnalyzerResult":
        start = self._start_timer()
        try:
            from ai.decision_engine import decide
            from ai.policy_engine import PolicyOutcome
            from ai.redactor import redact_text
            from ai.risk_engine import RiskAssessment, assess_risk
            from schemas.detection import Recommendation, Severity

            # 1. Get risk assessment from RiskFusionAnalyzer
            fusion_result = context.analyzer_results.get("RiskFusionAnalyzer")
            if fusion_result and fusion_result.status == AnalyzerStatus.SUCCESS:
                extra = fusion_result.extra or {}
                from schemas.detection import Severity as Sev
                risk_assessment = RiskAssessment(
                    overall_score=extra.get("overall_score", 0),
                    overall_severity=Sev(extra.get("overall_severity", "NONE")),
                    confidence=extra.get("confidence", 0.0),
                    reason=fusion_result.summary,
                    contributing_detectors=[
                        c["analyzer"] for c in extra.get("contributions", [])
                    ],
                )
            else:
                # Fallback to direct risk assessment if fusion failed
                risk_assessment = assess_risk(context.findings)

            # 2. Get policy outcome from ComplianceAnalyzer
            policy_outcome: PolicyOutcome | None = None
            compliance_result = context.analyzer_results.get("ComplianceAnalyzer")
            if compliance_result and compliance_result.status == AnalyzerStatus.SUCCESS:
                po_dict = (compliance_result.extra or {}).get("policy_outcome")
                if po_dict:
                    policy_outcome = PolicyOutcome(**po_dict)

            # 3. Make decision
            decision = decide(risk_assessment, policy_outcome, context.findings)
            context.decision = decision

            # 4. Redact prompt (only prompt-sourced results, not file-tagged ones)
            prompt_results = [r for r in context.findings if not r.reason.startswith("[file:")]
            if context.prompt.strip():
                context.sanitized_prompt = redact_text(context.prompt, prompt_results)
            else:
                context.sanitized_prompt = context.prompt

            elapsed = self._elapsed_ms(start)

            evidence = [Evidence(
                label="FINAL_DECISION",
                value_preview=(
                    f"{decision.action.value} | risk={decision.risk.value} "
                    f"| score={decision.score}"
                ),
                confidence=1.0,
                location="decision_engine",
                detector="decision",
                severity=decision.risk,
                metadata={
                    "action": decision.action.value,
                    "risk": decision.risk.value,
                    "score": decision.score,
                    "reason": decision.reason,
                    "triggered_rules_count": len(decision.triggered_rules),
                    "policy_triggered": policy_outcome is not None,
                    "policy_name": policy_outcome.policy_name if policy_outcome else None,
                },
            )]

            from schemas.detection import DetectionResult
            decision_finding = DetectionResult(
                detector="decision",
                severity=decision.risk,
                score=decision.score,
                matches=[],
                recommendation=decision.action,
                reason=decision.reason,
            )

            return self._success(
                [decision_finding],
                evidence,
                elapsed,
                summary=(
                    f"Decision: {decision.action.value} "
                    f"(risk={decision.risk.value}, score={decision.score}). "
                    f"{decision.reason}"
                ),
                extra={
                    "action": decision.action.value,
                    "risk": decision.risk.value,
                    "score": decision.score,
                    "reason": decision.reason,
                    "triggered_rules": decision.triggered_rules,
                },
            )

        except Exception as exc:
            logger.exception("DecisionAnalyzer failed")
            # Fallback: allow the scan with zero confidence
            from schemas.detection import Recommendation, Severity
            from ai.decision_engine import Decision
            context.decision = Decision(
                risk=Severity.NONE,
                score=0,
                action=Recommendation.ALLOW,
                reason=f"Decision engine failed: {exc}. Failing open.",
                triggered_rules=[],
            )
            context.sanitized_prompt = context.prompt
            return self._failed(str(exc), self._elapsed_ms(start))
