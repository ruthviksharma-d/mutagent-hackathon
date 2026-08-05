"""
PiiAnalyzer — runs PII detection on the prompt and extracted file text.

Wraps:
    ai/presidio_detector.py  — NLP-based PII (Presidio + spaCy en_core_web_sm)
    ai/spacy_detector.py     — spaCy NER (PERSON, ORG, GPE, LOC)
    ai/regex_detector.py     — structured patterns (email, phone, credit card only)

Produces structured Evidence per PII hit with value_preview, confidence,
location, and character offsets where available.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mutagent.analyzers.base import BaseAnalyzer
from mutagent.models import Evidence

if TYPE_CHECKING:
    from mutagent.models import AnalyzerResult, InvestigationContext

logger = logging.getLogger("promptshield.mutagent.pii_analyzer")

# Regex labels that constitute PII (not secrets/injection — those go to other analyzers)
_PII_REGEX_LABELS = {"EMAIL", "PHONE_NUMBER", "CREDIT_CARD"}


class PiiAnalyzer(BaseAnalyzer):
    """
    PII (Personally Identifiable Information) detector.

    Detects: emails, phone numbers, credit cards, passport numbers, SSNs,
    IBAN codes, person names, addresses, locations, and IP addresses.

    Evidence confidence is derived from detector score (0–100 → 0.0–1.0)
    and Presidio's own per-entity confidence score where available.
    """
    name = "PiiAnalyzer"
    display_name = "PII Agent"
    timeout_seconds = 2.0

    def run(self, context: "InvestigationContext") -> "AnalyzerResult":
        start = self._start_timer()
        try:
            from ai.presidio_detector import detect_presidio
            from ai.regex_detector import _PATTERNS, detect_regex
            from ai.spacy_detector import detect_spacy
            from schemas.detection import DetectionResult, Match, Recommendation, Severity

            text = context.prompt
            all_findings = []
            all_evidence: list[Evidence] = []

            # 1. Presidio (NLP-based PII)
            presidio_result = detect_presidio(text)
            if presidio_result.severity != Severity.NONE:
                all_findings.append(presidio_result)
                all_evidence.extend(self._make_evidence_from_results([presidio_result], "prompt"))

            # 2. spaCy NER
            spacy_result = detect_spacy(text)
            if spacy_result.severity != Severity.NONE:
                all_findings.append(spacy_result)
                all_evidence.extend(self._make_evidence_from_results([spacy_result], "prompt"))

            # 3. Regex — PII patterns only (email, phone, credit card)
            regex_result = detect_regex(text)
            pii_matches = [m for m in regex_result.matches if m.label in _PII_REGEX_LABELS]
            if pii_matches:
                from schemas.detection import SEVERITY_RANK
                filtered_severity = max(
                    (m.label for m in pii_matches),
                    key=lambda lbl: SEVERITY_RANK.get(
                        next((s for l, _, s, _ in _PATTERNS if l == lbl), Severity.NONE),
                        0,
                    ),
                    default=None,
                )
                # Build a filtered regex result scoped to PII labels only
                pii_score = min(sum(
                    score for lbl, _, _, score in _PATTERNS if lbl in _PII_REGEX_LABELS
                    for m in pii_matches if m.label == lbl
                ), 100)
                if pii_score > 0:
                    pii_result = DetectionResult(
                        detector="regex_pii",
                        severity=regex_result.severity,
                        score=pii_score,
                        matches=pii_matches,
                        recommendation=regex_result.recommendation,
                        reason=f"Regex PII detected: {', '.join(sorted({m.label for m in pii_matches}))}.",
                    )
                    all_findings.append(pii_result)
                    all_evidence.extend(self._make_evidence_from_results([pii_result], "prompt"))

            # Also scan extracted file text (populated by FileIntelAnalyzer)
            for file_input in context.uploaded_files:
                extracted_text = file_input.__dict__.get("_extracted_text", "")
                if not extracted_text:
                    continue
                source = f"file:{file_input.filename}"
                for result in [detect_presidio(extracted_text), detect_spacy(extracted_text)]:
                    if result.severity != Severity.NONE:
                        tagged = result.model_copy(update={"reason": f"[{source}] {result.reason}"})
                        all_findings.append(tagged)
                        all_evidence.extend(self._make_evidence_from_results([tagged], source))

            elapsed = self._elapsed_ms(start)
            context.add_findings(all_findings)
            return self._success(all_findings, all_evidence, elapsed)

        except Exception as exc:
            logger.exception("PiiAnalyzer failed")
            return self._failed(str(exc), self._elapsed_ms(start))
