"""
Pipeline Orchestrator — the official entry point for all prompt/file scanning.

Milestone v2 (Mutagent): run_pipeline_for_user() is the new primary entry
point, delegating to the InvestigationEngine which orchestrates the
multi-analyzer workflow. All existing helper functions and detector calls
below remain intact — the analyzers call them directly.

The original sequential pipeline logic is preserved here so:
  1. Analyzers can import and call individual detector functions directly.
  2. Existing unit tests that import ai.pipeline helpers still work.
  3. The architecture evolution is visible in one place.

File Scanning note: prompt and files are combined into ONE list of
DetectionResults before risk/policy/decision runs (see the module
docstring in ai/risk_engine.py and ai/decision_engine.py). Per-file
summaries are computed independently for the extension's per-file gating.
"""
import base64
import logging
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from ai.code_detector import detect_source_code
from ai.decision_engine import Decision, decide
from ai.file_risk import assess_disallowed_extension, assess_file_identity_risk
from ai.file_scanner import extract_text_from_file, get_file_category, infer_extension
from ai.keyword_detector import detect_company_keywords
from ai.normalizer import normalize_prompt
from ai.policy_engine import evaluate_policies
from ai.presidio_detector import detect_presidio
from ai.regex_detector import detect_regex
from ai.risk_engine import assess_risk
from ai.secret_detector import detect_secrets_in_text
from ai.semantic_classifier import classify_semantic_risk, should_run_semantic_classifier
from ai.spacy_detector import detect_spacy
from models.policy import Policy
from schemas.detection import DetectionResult, Recommendation, Severity
from schemas.scan import FileFindingSummary, ScanFileInput
from services.keyword_service import get_enabled_keywords
from services.policy_service import get_enabled_policies
from services.settings_service import get_or_create_settings

logger = logging.getLogger("promptshield.ai.pipeline")


@dataclass
class PipelineOutput:
    decision: Decision
    sanitized_prompt: str
    all_results: list[DetectionResult]
    file_findings: list[FileFindingSummary] = field(default_factory=list)


def _safe_call(detector_name: str, fn: Callable[[], DetectionResult]) -> DetectionResult:
    """
    Milestone 6 hardening: every detector used to be called directly, so an
    unexpected exception in any ONE of them (a malformed-unicode edge case,
    a third-party library bug, anything not already caught internally)
    took down the entire /api/scan request with a 500 - no audit log entry,
    and a security tool that fails a *legitimate* prompt because of its own
    bug is worse than one that logs the failure and keeps scanning with the
    other eight detectors. This wraps every detector call so one broken
    detector degrades to a neutral result instead of failing the whole scan.
    """
    try:
        return fn()
    except Exception:
        logger.exception("Detector '%s' raised an unhandled exception - degrading to a neutral result.", detector_name)
        return DetectionResult(
            detector=detector_name,
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason=f"{detector_name} detector failed unexpectedly and was skipped for this scan.",
        )


def _run_deterministic_detectors(text: str, keywords: list[str]) -> list[DetectionResult]:
    """Regex -> Presidio -> spaCy -> Source Code -> Company Keyword -> Secrets."""
    return [
        _safe_call("regex", lambda: detect_regex(text)),
        _safe_call("presidio", lambda: detect_presidio(text)),
        _safe_call("spacy", lambda: detect_spacy(text)),
        _safe_call("source_code", lambda: detect_source_code(text)),
        _safe_call("company_keyword", lambda: detect_company_keywords(text, keywords)),
        _safe_call("secrets", lambda: detect_secrets_in_text(text)),
    ]


def _tag_with_source(results: list[DetectionResult], source_label: str) -> list[DetectionResult]:
    """Prefix each result's reason with its origin (e.g. an uploaded file) while
    keeping the DetectionResult schema itself identical across the board."""
    tagged = []
    for r in results:
        tagged.append(r.model_copy(update={"reason": f"[{source_label}] {r.reason}"}))
    return tagged


def _scan_one_file(
    file_input: ScanFileInput,
    keywords: list[str],
    allowed_extensions: set[str],
    policies: list[Policy],
) -> tuple[list[DetectionResult], FileFindingSummary]:
    """Runs one uploaded file through identity-risk assessment and (if its
    extension is both allowed and extractable) the exact same content
    detectors the prompt itself uses. Returns the tagged DetectionResults to
    fold into the overall scan plus a FileFindingSummary - including this
    file's OWN independent action/reason (see FileFindingSummary's
    docstring) - for audit/dashboard purposes AND for the extension to gate
    each file individually rather than all-or-nothing."""
    filename = file_input.filename
    extension = infer_extension(filename)
    category = get_file_category(filename)
    source_label = f"file:{filename}"

    file_results: list[DetectionResult] = []

    # 1. Org-level allow-list (services/settings_service.py -> OrgSettings.
    #    allowed_file_types) is checked FIRST and short-circuits extraction -
    #    an admin who has explicitly disallowed a file type shouldn't have
    #    its contents parsed at all, just rejected.
    if extension and extension not in allowed_extensions:
        file_results.append(assess_disallowed_extension(filename))
        extracted = False
        extraction_note = f"File type '.{extension}' is not in the organization's allowed file types."
    else:
        # 2. Identity risk (e.g. .env, private keys, docker-compose.yml) -
        #    independent of whether extraction below succeeds.
        identity_result = assess_file_identity_risk(filename)
        if identity_result.severity != Severity.NONE:
            file_results.append(identity_result)

        # 3. Content: extract text, then run it through the SAME detector
        #    pipeline as a typed prompt (no duplicated detection logic).
        extraction = extract_text_from_file(filename, file_input.content_base64)
        extracted = extraction.success and bool(extraction.text.strip())
        extraction_note = None if extraction.success else extraction.reason

        if extracted:
            file_normalized = normalize_prompt(extraction.text).normalized
            file_results.extend(_run_deterministic_detectors(file_normalized, keywords))
        elif not extraction.success:
            extraction_note = extraction.reason

    tagged = _tag_with_source(file_results, source_label)

    # Per-file decision: this file's OWN risk assessment, policy match, and
    # decision - computed from ONLY this file's findings, completely
    # independent of the prompt and every other file in the same request.
    # This is what lets a batch of five files upload the four clean ones
    # and hold back just the risky one, instead of one bad file vetoing the
    # whole batch. It never feeds into the overall Decision a second time
    # (that's computed once, over every result from prompt + all files
    # combined, in run_pipeline) - the two are deliberately separate:
    # the overall decision still gates the PROMPT TEXT (unified across
    # everything attached, per the original File Scanning spec), while this
    # per-file decision is what the extension acts on to gate each FILE.
    per_file_risk = assess_risk(file_results)
    per_file_policy_outcome = evaluate_policies(file_results, policies)
    per_file_decision = decide(per_file_risk, per_file_policy_outcome, file_results)

    size_bytes = file_input.size_bytes
    if size_bytes is None:
        # Fall back to the decoded size so audit logs always have a number
        # even if the extension client didn't send one.
        try:
            size_bytes = len(base64.b64decode(file_input.content_base64, validate=False))
        except Exception:
            size_bytes = None

    summary = FileFindingSummary(
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
    )

    return tagged, summary


def run_pipeline_for_user(
    db: Session,
    user,
    prompt: str,
    site: str,
    files: list[ScanFileInput],
) -> PipelineOutput:
    """
    Primary entry point for prompt/file scanning (Mutagent v2).

    Delegates to InvestigationEngine which orchestrates the multi-analyzer
    workflow. All existing detector functions in this module remain available
    for direct use by the analyzers.

    Called from routers/scan.py.
    """
    from mutagent.engine import InvestigationEngine
    return InvestigationEngine(db).run(
        user=user, prompt=prompt, site=site, files=files
    )


def run_pipeline(db: Session, prompt: str, site: str, files: list[ScanFileInput]) -> PipelineOutput:
    """
    Legacy entry point — preserved for backward compatibility with any
    direct callers outside routers/scan.py. New code should use
    run_pipeline_for_user() which passes the user to the engine so
    investigation traces are correctly attributed.

    routers/scan.py was updated in Mutagent v2 to call
    run_pipeline_for_user() directly.
    """
    # This path cannot build a proper InvestigationContext without a user,
    # so it falls back to the original sequential implementation for safety.
    normalized = normalize_prompt(prompt)
    text = normalized.normalized

    keywords = get_enabled_keywords(db)
    org_settings = get_or_create_settings(db)
    allowed_extensions = {ext.lower().lstrip(".") for ext in (org_settings.allowed_file_types or [])}
    policies = get_enabled_policies(db)

    all_results: list[DetectionResult] = list(_run_deterministic_detectors(text, keywords)) if text.strip() else []

    file_findings: list[FileFindingSummary] = []
    for file_input in files:
        tagged_results, summary = _scan_one_file(file_input, keywords, allowed_extensions, policies)
        all_results.extend(tagged_results)
        file_findings.append(summary)

    if text.strip() and should_run_semantic_classifier(all_results):
        all_results.append(_safe_call("semantic", lambda: classify_semantic_risk(text)))

    risk_assessment = assess_risk(all_results)
    policy_outcome = evaluate_policies(all_results, policies)
    decision = decide(risk_assessment, policy_outcome, all_results)

    from ai.redactor import redact_text
    prompt_sourced_results = [r for r in all_results if not r.reason.startswith("[file:")]
    sanitized_prompt = redact_text(text, prompt_sourced_results) if text.strip() else text

    return PipelineOutput(
        decision=decision,
        sanitized_prompt=sanitized_prompt,
        all_results=all_results,
        file_findings=file_findings,
    )
