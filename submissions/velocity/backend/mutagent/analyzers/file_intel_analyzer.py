"""
FileIntelAnalyzer — Stage 2 of the investigation workflow.

Responsibility: file identity risk assessment and text extraction.
Extraction is deliberately separated from content analysis (Stages 3+)
so the audit trail shows clearly when a file was risky by identity alone
(e.g. uploading a bare .env file) versus risky by content.

Populates:
    context.file_findings  — per-file FileFindingSummary records
    context.findings        — tagged DetectionResult entries for file risks

Does NOT run content detectors — that's PiiAnalyzer, SecretsAnalyzer, etc.
Text extracted here is stored in context for use by Stage 3 analyzers via
the findings already tagged with [file:<name>] prefixes.
"""
from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from mutagent.analyzers.base import BaseAnalyzer
from mutagent.models import AnalyzerResult, AnalyzerStatus, Evidence
from schemas.detection import Recommendation, Severity

if TYPE_CHECKING:
    from mutagent.models import InvestigationContext

logger = logging.getLogger("promptshield.mutagent.file_intel_analyzer")


class FileIntelAnalyzer(BaseAnalyzer):
    """
    File Intelligence — determines file type, category, and identity risk.
    Extracts text from supported file types for downstream content analyzers.

    Supported: PDF, DOCX, PPTX, XLSX, CSV, JSON, TXT, Images (OCR),
               source code, configuration files, .env, ZIP (rejected).
    """
    name = "FileIntelAnalyzer"
    display_name = "File Intelligence Agent"
    timeout_seconds = 5.0  # OCR can be slow

    def run(self, context: "InvestigationContext") -> AnalyzerResult:
        start = self._start_timer()

        if not context.uploaded_files:
            return AnalyzerResult(
                agent_name=self.name,
                display_name=self.display_name,
                status=AnalyzerStatus.SUCCESS,
                execution_time_ms=self._elapsed_ms(start),
                confidence=1.0,
                severity=Severity.NONE,
                findings=[],
                evidence=[],
                recommendation=Recommendation.ALLOW,
                summary="No files uploaded — file analysis skipped.",
            )

        try:
            from ai.decision_engine import decide
            from ai.file_risk import assess_disallowed_extension, assess_file_identity_risk
            from ai.file_scanner import extract_text_from_file, get_file_category, infer_extension
            from ai.normalizer import normalize_prompt
            from ai.policy_engine import evaluate_policies
            from ai.risk_engine import assess_risk
            from schemas.scan import FileFindingSummary

            org_settings = context.org_settings
            allowed_extensions = {
                ext.lower().lstrip(".")
                for ext in (getattr(org_settings, "allowed_file_types", None) or [])
            }

            all_file_results = []
            all_evidence: list[Evidence] = []
            file_summaries = []

            for file_input in context.uploaded_files:
                filename = file_input.filename
                extension = infer_extension(filename)
                category = get_file_category(filename)
                source_label = f"file:{filename}"
                file_results = []

                # 1. Allowed-extension check
                if extension and allowed_extensions and extension not in allowed_extensions:
                    dr = assess_disallowed_extension(filename)
                    file_results.append(dr)
                    extracted = False
                    extraction_note = f"File type '.{extension}' not in allowed file types."
                else:
                    # 2. Identity risk
                    identity_result = assess_file_identity_risk(filename)
                    if identity_result.severity != Severity.NONE:
                        file_results.append(identity_result)

                    # 3. Text extraction
                    extraction = extract_text_from_file(filename, file_input.content_base64)
                    extracted = extraction.success and bool(extraction.text.strip())
                    extraction_note = None if extraction.success else extraction.reason

                    if extracted:
                        # Store extracted text back in the file_input for downstream analyzers
                        file_input.__dict__["_extracted_text"] = normalize_prompt(extraction.text).normalized

                # Tag results with source
                tagged = [
                    r.model_copy(update={"reason": f"[{source_label}] {r.reason}"})
                    for r in file_results
                ]
                all_file_results.extend(tagged)
                all_evidence.extend(self._make_evidence_from_results(tagged, source_label))

                # Per-file decision
                per_file_risk = assess_risk(file_results)
                per_file_policy = evaluate_policies(file_results, context.policies)
                per_file_decision = decide(per_file_risk, per_file_policy, file_results)

                # Compute size
                size_bytes = file_input.size_bytes
                if size_bytes is None:
                    try:
                        size_bytes = len(base64.b64decode(file_input.content_base64, validate=False))
                    except Exception:
                        size_bytes = None

                file_summaries.append(FileFindingSummary(
                    filename=filename,
                    extension=extension or "",
                    category=category,
                    size_bytes=size_bytes,
                    mime_type=file_input.mime_type,
                    risk=per_file_risk.overall_severity.value,
                    score=per_file_risk.overall_score,
                    action=per_file_decision.action.value,
                    reason=per_file_decision.reason,
                    extracted=extracted,
                    extraction_note=extraction_note,
                ))

            # Populate shared context
            context.file_findings.extend(file_summaries)
            context.add_findings(all_file_results)

            elapsed = self._elapsed_ms(start)
            n_files = len(context.uploaded_files)
            n_risky = sum(1 for f in file_summaries if f.risk not in ("NONE", "LOW"))

            return self._success(
                all_file_results,
                all_evidence,
                elapsed,
                summary=(
                    f"Analyzed {n_files} file(s): "
                    f"{n_risky} high-risk, "
                    f"{n_files - n_risky} clean."
                ),
            )

        except Exception as exc:
            logger.exception("FileIntelAnalyzer failed")
            return self._failed(str(exc), self._elapsed_ms(start))
