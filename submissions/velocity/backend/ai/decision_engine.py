"""
Decision Engine - the final stage before redaction/audit-logging. Combines
the Risk Engine's severity-based assessment with any Policy Engine
override into ONE unified decision.

Precedence: an enabled policy match always wins over the default
severity-to-action mapping, since policies represent explicit admin intent.
"""
from pydantic import BaseModel

from ai.policy_engine import PolicyOutcome
from ai.risk_engine import RiskAssessment
from schemas.detection import DetectionResult, Recommendation, Severity

_DEFAULT_ACTION_BY_SEVERITY: dict[Severity, Recommendation] = {
    Severity.NONE: Recommendation.ALLOW,
    Severity.LOW: Recommendation.ALLOW,
    Severity.MEDIUM: Recommendation.WARN,
    Severity.HIGH: Recommendation.REDACT,
    Severity.CRITICAL: Recommendation.BLOCK,
}


class Decision(BaseModel):
    risk: Severity
    score: int
    action: Recommendation
    reason: str
    triggered_rules: list[dict]


def decide(
    risk_assessment: RiskAssessment,
    policy_outcome: PolicyOutcome | None,
    results: list[DetectionResult],
) -> Decision:
    if policy_outcome is not None:
        action = policy_outcome.action
        reason = policy_outcome.reason
    else:
        action = _DEFAULT_ACTION_BY_SEVERITY[risk_assessment.overall_severity]
        reason = risk_assessment.reason

    triggered_rules = [
        {
            "detector": r.detector,
            "severity": r.severity.value,
            "score": r.score,
            "reason": r.reason,
        }
        for r in results
        if r.severity != Severity.NONE
    ]

    return Decision(
        risk=risk_assessment.overall_severity,
        score=risk_assessment.overall_score,
        action=action,
        reason=reason,
        triggered_rules=triggered_rules,
    )
