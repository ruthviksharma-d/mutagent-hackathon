"""
Company Keyword Detector - flags org-specific sensitive terms (project
codenames, internal classifications, etc.) loaded fresh from MySQL on
every scan so admins can add/remove keywords without a redeploy.
"""
import re

from schemas.detection import DetectionResult, Match, Recommendation, Severity

_SCORE_PER_HIT = 40  # matches the example in the Milestone 2 spec


def detect_company_keywords(text: str, keywords: list[str]) -> DetectionResult:
    if not keywords:
        return DetectionResult(
            detector="company_keyword",
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason="No company keywords configured.",
        )

    matches: list[Match] = []
    hit_keywords: set[str] = set()

    for keyword in keywords:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        for m in pattern.finditer(text):
            matches.append(Match(label="COMPANY_KEYWORD", value_preview=keyword, start=m.start(), end=m.end()))
            hit_keywords.add(keyword)

    if not matches:
        return DetectionResult(
            detector="company_keyword",
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason="No company keywords found in prompt.",
        )

    score = min(len(hit_keywords) * _SCORE_PER_HIT, 100)
    severity = Severity.CRITICAL if score >= 80 else Severity.HIGH if score >= 40 else Severity.MEDIUM

    return DetectionResult(
        detector="company_keyword",
        severity=severity,
        score=score,
        matches=matches,
        recommendation=Recommendation.BLOCK if severity == Severity.CRITICAL else Recommendation.WARN,
        reason=f"Company-sensitive terms found: {', '.join(sorted(hit_keywords))}.",
    )
