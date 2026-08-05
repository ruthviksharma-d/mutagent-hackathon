"""
SecretsAnalyzer — detects credentials, tokens, and secrets in prompts and files.

Wraps:
    ai/secret_detector.py   — detect-secrets (AWS, GitHub, private keys, etc.)
    ai/regex_detector.py    — credential patterns (API keys, JWT, passwords, DB strings)

All secret values are masked before being stored as evidence — only a
preview (e.g. "AKIA****", "hash:abc123...") ever reaches the Evidence object.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mutagent.analyzers.base import BaseAnalyzer
from mutagent.models import Evidence

if TYPE_CHECKING:
    from mutagent.models import AnalyzerResult, InvestigationContext

logger = logging.getLogger("promptshield.mutagent.secrets_analyzer")

# Regex labels that are credential/secret (not generic PII)
_SECRET_REGEX_LABELS = {
    "AWS_ACCESS_KEY", "AWS_SECRET_KEY", "GITHUB_TOKEN", "GOOGLE_API_KEY",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "HUGGINGFACE_TOKEN",
    "REPLICATE_API_TOKEN", "GROQ_API_KEY", "PERPLEXITY_API_KEY",
    "NOTION_API_KEY", "SLACK_WEBHOOK_URL", "DISCORD_WEBHOOK_URL",
    "DB_CONNECTION_STRING", "JWT_TOKEN", "GENERIC_API_KEY", "BEARER_TOKEN",
    "PASSWORD",
}


class SecretsAnalyzer(BaseAnalyzer):
    """
    Secrets and credential leak detector.

    Detects: AWS keys, OpenAI/Anthropic/Hugging Face tokens, GitHub/GitLab
    tokens, JWT tokens, passwords, private keys, certificates, database
    connection strings, and entropy-based secrets via detect-secrets.

    Values are always masked before storage — never stored raw.
    """
    name = "SecretsAnalyzer"
    display_name = "Secrets Agent"
    timeout_seconds = 2.0

    def run(self, context: "InvestigationContext") -> "AnalyzerResult":
        start = self._start_timer()
        try:
            from ai.regex_detector import _PATTERNS, detect_regex
            from ai.secret_detector import detect_secrets_in_text
            from schemas.detection import DetectionResult, Severity

            text = context.prompt
            all_findings = []
            all_evidence: list[Evidence] = []

            # 1. detect-secrets (AWS, GitHub, private keys, service tokens)
            secrets_result = detect_secrets_in_text(text)
            if secrets_result.severity != Severity.NONE:
                all_findings.append(secrets_result)
                all_evidence.extend(self._make_evidence_from_results([secrets_result], "prompt"))

            # 2. Regex — secrets/credential patterns only
            regex_result = detect_regex(text)
            secret_matches = [m for m in regex_result.matches if m.label in _SECRET_REGEX_LABELS]
            if secret_matches:
                secret_score = min(sum(
                    score for lbl, _, _, score in _PATTERNS if lbl in _SECRET_REGEX_LABELS
                    for m in secret_matches if m.label == lbl
                ), 100)
                if secret_score > 0:
                    from schemas.detection import SEVERITY_RANK
                    sev_values = [
                        sev for lbl, _, sev, _ in _PATTERNS
                        if lbl in {m.label for m in secret_matches}
                    ]
                    highest = max(sev_values, key=lambda s: SEVERITY_RANK[s], default=Severity.NONE)
                    secret_result = DetectionResult(
                        detector="regex_secrets",
                        severity=highest,
                        score=secret_score,
                        matches=secret_matches,
                        recommendation=regex_result.recommendation,
                        reason=f"Credentials detected: {', '.join(sorted({m.label for m in secret_matches}))}.",
                    )
                    all_findings.append(secret_result)
                    all_evidence.extend(self._make_evidence_from_results([secret_result], "prompt"))

            # 3. Scan extracted file text
            for file_input in context.uploaded_files:
                extracted_text = file_input.__dict__.get("_extracted_text", "")
                if not extracted_text:
                    continue
                source = f"file:{file_input.filename}"
                for result in [
                    detect_secrets_in_text(extracted_text),
                    detect_regex(extracted_text),
                ]:
                    # For regex on files, keep only secret labels
                    if result.detector == "regex":
                        file_secret_matches = [m for m in result.matches if m.label in _SECRET_REGEX_LABELS]
                        if not file_secret_matches:
                            continue
                        result = result.model_copy(update={
                            "matches": file_secret_matches,
                            "reason": f"[{source}] Credentials: {', '.join(sorted({m.label for m in file_secret_matches}))}."
                        })
                    elif result.severity == Severity.NONE:
                        continue
                    else:
                        result = result.model_copy(update={"reason": f"[{source}] {result.reason}"})
                    all_findings.append(result)
                    all_evidence.extend(self._make_evidence_from_results([result], source))

            elapsed = self._elapsed_ms(start)
            context.add_findings(all_findings)
            return self._success(all_findings, all_evidence, elapsed)

        except Exception as exc:
            logger.exception("SecretsAnalyzer failed")
            return self._failed(str(exc), self._elapsed_ms(start))
