"""
ComplianceAnalyzer — enforces org-specific policies and keyword rules.

Wraps:
    ai/keyword_detector.py — company-specific sensitive term detection
    ai/policy_engine.py    — admin-authored policy rules

The PolicyOutcome is stored in the AnalyzerResult.extra dict so that
DecisionAnalyzer can retrieve it for the final decision (policies always
override risk-based defaults, per the existing engine logic).

This runs after the analysis stage so it can evaluate policies against
findings already collected from PII, Secrets, and Injection analyzers.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mutagent.analyzers.base import BaseAnalyzer
from mutagent.models import Evidence

if TYPE_CHECKING:
    from mutagent.models import AnalyzerResult, InvestigationContext

logger = logging.getLogger("promptshield.mutagent.compliance_analyzer")


class ComplianceAnalyzer(BaseAnalyzer):
    """
    Compliance and policy enforcement analyzer.

    Checks:
    - Company keyword violations (admin-configured sensitive terms)
    - Policy rule matches against all findings from this investigation
    - Data classification and confidentiality policy enforcement
    """
    name = "ComplianceAnalyzer"
    display_name = "Compliance Agent"
    timeout_seconds = 2.0

    def run(self, context: "InvestigationContext") -> "AnalyzerResult":
        start = self._start_timer()
        try:
            from ai.keyword_detector import detect_company_keywords
            from ai.policy_engine import evaluate_policies
            from schemas.detection import Severity

            text = context.prompt
            all_findings = []
            all_evidence: list[Evidence] = []

            # 1. Company keyword detection
            keyword_result = detect_company_keywords(text, context.keywords)
            if keyword_result.severity != Severity.NONE:
                all_findings.append(keyword_result)
                all_evidence.extend(
                    self._make_evidence_from_results([keyword_result], "prompt")
                )

            # Also scan extracted file text
            for file_input in context.uploaded_files:
                extracted_text = file_input.__dict__.get("_extracted_text", "")
                if not extracted_text:
                    continue
                source = f"file:{file_input.filename}"
                file_kw_result = detect_company_keywords(extracted_text, context.keywords)
                if file_kw_result.severity != Severity.NONE:
                    tagged = file_kw_result.model_copy(update={
                        "reason": f"[{source}] {file_kw_result.reason}"
                    })
                    all_findings.append(tagged)
                    all_evidence.extend(self._make_evidence_from_results([tagged], source))

            # 2. Policy evaluation against ALL findings in context so far
            all_current_findings = list(context.findings) + all_findings
            policy_outcome = evaluate_policies(all_current_findings, context.policies)

            # Build a policy evidence item if a policy fired
            policy_evidence_extra: dict = {}
            if policy_outcome is not None:
                policy_evidence_extra = {
                    "policy_id": policy_outcome.policy_id,
                    "policy_name": policy_outcome.policy_name,
                    "action": policy_outcome.action.value,
                    "reason": policy_outcome.reason,
                }
                all_evidence.append(Evidence(
                    label="POLICY_TRIGGERED",
                    value_preview=f"Policy: {policy_outcome.policy_name}",
                    confidence=1.0,
                    location="policy_engine",
                    detector="policy",
                    severity=Severity.HIGH,
                    metadata=policy_evidence_extra,
                ))

            context.add_findings(all_findings)
            elapsed = self._elapsed_ms(start)

            # Serialize policy_outcome so DecisionAnalyzer can use it
            extra = {
                "policy_outcome": (
                    policy_outcome.model_dump() if policy_outcome else None
                )
            }

            policy_summary = (
                f"Policy '{policy_outcome.policy_name}' triggered → {policy_outcome.action.value}."
                if policy_outcome
                else "No policies triggered."
            )
            kw_summary = (
                f"Company keywords detected." if any(
                    "company_keyword" in f.detector for f in all_findings
                ) else "No company keywords found."
            )

            return self._success(
                all_findings,
                all_evidence,
                elapsed,
                summary=f"{kw_summary} {policy_summary}".strip(),
                extra=extra,
            )

        except Exception as exc:
            logger.exception("ComplianceAnalyzer failed")
            return self._failed(str(exc), self._elapsed_ms(start))
