"""
Risk Engine - aggregates every DetectionResult produced by the pipeline
into one overall assessment. This is pure aggregation: it does not know
about policies, MySQL, or the extension - it only reasons about the
DetectionResult objects it's handed.
"""
from pydantic import BaseModel

from schemas.detection import DetectionResult, Severity



class RiskAssessment(BaseModel):
    overall_score: int
    overall_severity: Severity
    confidence: float  # 0.0 - 1.0: how many independent detectors corroborated the finding
    reason: str
    contributing_detectors: list[str]


def _score_to_severity(score: int) -> Severity:
    if score >= 75:
        return Severity.CRITICAL
    if score >= 50:
        return Severity.HIGH
    if score >= 25:
        return Severity.MEDIUM
    if score > 0:
        return Severity.LOW
    return Severity.NONE


def assess_risk(results: list[DetectionResult]) -> RiskAssessment:
    if not results:
        return RiskAssessment(
            overall_score=0,
            overall_severity=Severity.NONE,
            confidence=0.0,
            reason="No detectors ran.",
            contributing_detectors=[],
        )

    contributing = [r for r in results if r.severity != Severity.NONE]
    total_score = min(sum(r.score for r in results), 100)
    overall_severity = _score_to_severity(total_score)
    confidence = round(len(contributing) / len(results), 2) if results else 0.0

    if not contributing:
        reason = "No sensitive content detected across regex, PII, NER, code, keyword, or secret scans."
    else:
        top = sorted(contributing, key=lambda r: r.score, reverse=True)[:3]
        reason = "; ".join(f"{r.detector} ({r.severity.value}, +{r.score}): {r.reason}" for r in top)

    return RiskAssessment(
        overall_score=total_score,
        overall_severity=overall_severity,
        confidence=confidence,
        reason=reason,
        contributing_detectors=[r.detector for r in contributing],
    )
