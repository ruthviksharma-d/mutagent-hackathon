"""
Presidio Detector - Microsoft Presidio's NLP-based PII recognizers layered
on top of the same spaCy model used by the spaCy NER Detector. Catches
PERSON, LOCATION/ADDRESS, EMAIL, CREDIT_CARD, PHONE, IP_ADDRESS, PASSPORT,
DATE_TIME and the rest of Presidio's default recognizer set.

Requires en_core_web_sm (see ai/nlp_loader.py). If it isn't installed,
this detector degrades to a neutral no-op result instead of crashing the
pipeline - the regex detector still independently catches emails/phones.
"""
import logging
from functools import lru_cache

from ai.nlp_loader import MODEL_NAME, is_nlp_available
from schemas.detection import SEVERITY_RANK, DetectionResult, Match, Recommendation, Severity

logger = logging.getLogger("promptshield.ai.presidio")

# Presidio entity -> our severity/score. Anything not listed defaults to LOW/5.
_ENTITY_WEIGHTS: dict[str, tuple[Severity, int]] = {
    "PERSON": (Severity.LOW, 8),
    "LOCATION": (Severity.LOW, 6),
    "ADDRESS": (Severity.MEDIUM, 15),
    "EMAIL_ADDRESS": (Severity.LOW, 8),
    "PHONE_NUMBER": (Severity.LOW, 8),
    "CREDIT_CARD": (Severity.HIGH, 30),
    "IP_ADDRESS": (Severity.MEDIUM, 12),
    "US_PASSPORT": (Severity.HIGH, 30),
    "US_SSN": (Severity.CRITICAL, 40),
    "DATE_TIME": (Severity.NONE, 2),
    "IBAN_CODE": (Severity.HIGH, 25),
    "MEDICAL_LICENSE": (Severity.HIGH, 25),
}



@lru_cache
def _get_analyzer():
    """Build the AnalyzerEngine once per process, reusing en_core_web_sm."""
    if not is_nlp_available():
        return None
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider

        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": MODEL_NAME}],
            }
        )
        return AnalyzerEngine(nlp_engine=provider.create_engine())
    except Exception as exc:
        logger.warning("Presidio AnalyzerEngine could not be initialized: %s", exc)
        return None


def _mask(value: str) -> str:
    if len(value) <= 6:
        return value[0] + "*" * (len(value) - 1) if value else value
    return f"{value[:3]}{'*' * (len(value) - 6)}{value[-3:]}"


def detect_presidio(text: str) -> DetectionResult:
    analyzer = _get_analyzer()
    if analyzer is None:
        return DetectionResult(
            detector="presidio",
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason=f"Presidio unavailable - {MODEL_NAME} not installed. Run `python -m spacy download {MODEL_NAME}`.",
        )

    results = analyzer.analyze(text=text, language="en")

    matches: list[Match] = []
    total_score = 0
    highest_severity = Severity.NONE
    hit_labels: set[str] = set()

    for r in results:
        severity, score = _ENTITY_WEIGHTS.get(r.entity_type, (Severity.LOW, 5))
        weighted_score = int(score * r.score)  # r.score is Presidio's own confidence (0-1)
        value = text[r.start : r.end]

        matches.append(Match(label=r.entity_type, value_preview=_mask(value), start=r.start, end=r.end))
        total_score += weighted_score
        hit_labels.add(r.entity_type)
        if SEVERITY_RANK[severity] > SEVERITY_RANK[highest_severity]:
            highest_severity = severity

    total_score = min(total_score, 100)

    if not matches:
        return DetectionResult(
            detector="presidio",
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason="No PII entities detected by Presidio.",
        )

    recommendation = (
        Recommendation.BLOCK
        if highest_severity == Severity.CRITICAL
        else Recommendation.REDACT
        if highest_severity in {Severity.HIGH, Severity.MEDIUM}
        else Recommendation.WARN
    )

    return DetectionResult(
        detector="presidio",
        severity=highest_severity,
        score=total_score,
        matches=matches,
        recommendation=recommendation,
        reason=f"Presidio detected: {', '.join(sorted(hit_labels))}.",
    )
