"""
The ONE common schema every detector in the AI Detection Engine must return.
The Risk Engine, Policy Engine, and Redactor all consume DetectionResult
objects exclusively through this shape - no detector is allowed to invent
its own response format.
"""
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Recommendation(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    REDACT = "REDACT"
    BLOCK = "BLOCK"


# Shared ranking used by every detector (and the Risk Engine) to compare
# severities and track a running "highest severity seen so far". Milestone 6
# hardening: this exact dict literal used to be copy-pasted independently
# into regex_detector.py, presidio_detector.py, spacy_detector.py,
# secret_detector.py, and risk_engine.py - defined once here instead so
# there's a single place to update if a severity level is ever added.
SEVERITY_RANK: dict[Severity, int] = {
    Severity.NONE: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class Match(BaseModel):
    """A single matched span within the scanned text."""

    label: str  # e.g. "EMAIL", "AWS_SECRET_KEY", "PERSON"
    # The raw matched value is intentionally NOT stored here in full for
    # high-sensitivity categories (secrets, credit cards) - detectors mask
    # it before it ever reaches this object. See detector docstrings.
    value_preview: str
    start: int | None = None  # character offset in the normalized text
    end: int | None = None


class DetectionResult(BaseModel):
    detector: str  # "regex" | "presidio" | "spacy" | "source_code" | "company_keyword" | "secrets" | "semantic" | "file:<name>"
    severity: Severity
    score: int = Field(ge=0, le=100)
    matches: list[Match] = []
    recommendation: Recommendation
    reason: str
