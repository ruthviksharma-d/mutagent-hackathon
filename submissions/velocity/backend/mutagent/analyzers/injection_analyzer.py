"""
InjectionAnalyzer — detects prompt injection attacks, jailbreak attempts,
and source code leakage in AI-bound prompts.

Wraps:
    ai/semantic_classifier.py — OpenRouter LLM-based semantic risk classification
    ai/code_detector.py       — source code leakage detection

The semantic classifier is the only detector that costs money/latency —
it is ONLY called when traditional detectors are inconclusive (same guard
as the old pipeline). If OPENROUTER_API_KEY is not configured, it skips
gracefully.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mutagent.analyzers.base import BaseAnalyzer
from mutagent.models import Evidence

if TYPE_CHECKING:
    from mutagent.models import AnalyzerResult, InvestigationContext

logger = logging.getLogger("promptshield.mutagent.injection_analyzer")


class InjectionAnalyzer(BaseAnalyzer):
    """
    Prompt Injection and Jailbreak detector.

    Detects:
    - "Ignore previous instructions" style injection attempts
    - System prompt extraction attempts
    - Role manipulation and persona hijacking
    - Jailbreak patterns via semantic classification
    - Source code leakage in prompts
    """
    name = "InjectionAnalyzer"
    display_name = "Prompt Injection Agent"
    timeout_seconds = 3.0  # semantic call has network latency

    def run(self, context: "InvestigationContext") -> "AnalyzerResult":
        start = self._start_timer()
        try:
            from ai.code_detector import detect_source_code
            from ai.semantic_classifier import (
                classify_semantic_risk,
                should_run_semantic_classifier,
            )
            from schemas.detection import Severity

            text = context.prompt
            all_findings = []
            all_evidence: list[Evidence] = []

            # 1. Source code leakage
            code_result = detect_source_code(text)
            if code_result.severity != Severity.NONE:
                all_findings.append(code_result)
                all_evidence.extend(self._make_evidence_from_results([code_result], "prompt"))

            # 2. Semantic classifier — only when inconclusive
            # Pass all findings seen so far (including from other analyzers
            # already in context) to decide whether to run.
            prior_results = list(context.findings) + all_findings
            if text.strip() and should_run_semantic_classifier(prior_results):
                semantic_result = classify_semantic_risk(text)
                if semantic_result.severity != Severity.NONE:
                    all_findings.append(semantic_result)
                    all_evidence.append(Evidence(
                        label="SEMANTIC_RISK",
                        value_preview=semantic_result.reason[:120],
                        confidence=min(semantic_result.score / 100, 1.0),
                        location="prompt",
                        detector="semantic",
                        severity=semantic_result.severity,
                        metadata={
                            "model": (
                                semantic_result.matches[0].value_preview
                                if semantic_result.matches else "unknown"
                            ),
                            "reason": semantic_result.reason,
                        },
                    ))

            elapsed = self._elapsed_ms(start)
            context.add_findings(all_findings)
            return self._success(all_findings, all_evidence, elapsed)

        except Exception as exc:
            logger.exception("InjectionAnalyzer failed")
            return self._failed(str(exc), self._elapsed_ms(start))
