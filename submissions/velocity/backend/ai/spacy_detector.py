"""
spaCy NER Detector - general named-entity recognition for organizations,
locations, people, products, and dates. Lower severity than Presidio's
PII-focused detection on its own, but valuable corroborating signal for
the Risk Engine (e.g. a prompt naming a real organization + a product
codename together is a stronger signal than either alone).

Requires en_core_web_sm - degrades to a neutral no-op result if missing.
"""
import logging

from ai.nlp_loader import MODEL_NAME, get_nlp
from schemas.detection import SEVERITY_RANK, DetectionResult, Match, Recommendation, Severity

logger = logging.getLogger("promptshield.ai.spacy")

_LABEL_WEIGHTS: dict[str, tuple[Severity, int]] = {
    "ORG": (Severity.LOW, 8),
    "GPE": (Severity.LOW, 5),   # countries, cities, states
    "LOC": (Severity.LOW, 5),
    "PERSON": (Severity.LOW, 8),
    "PRODUCT": (Severity.LOW, 6),
    "DATE": (Severity.NONE, 1),
}


def detect_spacy(text: str) -> DetectionResult:
    nlp = get_nlp()
    if nlp is None:
        return DetectionResult(
            detector="spacy",
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason=f"spaCy unavailable - {MODEL_NAME} not installed. Run `python -m spacy download {MODEL_NAME}`.",
        )

    doc = nlp(text)
    matches: list[Match] = []
    total_score = 0
    highest_severity = Severity.NONE
    hit_labels: set[str] = set()

    for ent in doc.ents:
        if ent.label_ not in _LABEL_WEIGHTS:
            continue
        severity, score = _LABEL_WEIGHTS[ent.label_]
        matches.append(
            Match(label=ent.label_, value_preview=ent.text, start=ent.start_char, end=ent.end_char)
        )
        total_score += score
        hit_labels.add(ent.label_)
        if SEVERITY_RANK[severity] > SEVERITY_RANK[highest_severity]:
            highest_severity = severity

    total_score = min(total_score, 100)

    if not matches:
        return DetectionResult(
            detector="spacy",
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason="No named entities detected.",
        )

    recommendation = Recommendation.WARN if highest_severity != Severity.NONE else Recommendation.ALLOW

    return DetectionResult(
        detector="spacy",
        severity=highest_severity,
        score=total_score,
        matches=matches,
        recommendation=recommendation,
        reason=f"Named entities found: {', '.join(sorted(hit_labels))}.",
    )
