"""
Secret Detector - wraps Yelp's `detect-secrets` engine (the same plugin set
used by its pre-commit hook) for AWS credentials, GitHub tokens, private
keys / SSH keys / certificates (PrivateKeyDetector), and database
connection strings / basic-auth URLs (BasicAuthDetector, KeywordDetector).

Deliberately EXCLUDES detect-secrets' Base64HighEntropyString and
HexHighEntropyString plugins: those are tuned for scanning source files
line-by-line, not natural-language prose, and in testing they fired on
plain English words (e.g. "banana") because ordinary sentences have
similar character-level entropy to short encoded tokens once you strip
whitespace. Every credential format those two plugins would have caught
in practice (AWS/GitHub/Google/OpenAI keys, JWTs) is already covered
precisely by ai/regex_detector.py, so nothing is lost by leaving them out.

detect-secrets is designed to scan files, so we feed it the prompt
line-by-line via its lower-level scan_line() API. By design it only ever
returns a *hash* of the secret, never the raw value - which is exactly the
safety property we want for anything that touches audit logs.
"""
import logging

from schemas.detection import SEVERITY_RANK, DetectionResult, Match, Recommendation, Severity

logger = logging.getLogger("promptshield.ai.secrets")


# Deterministic, pattern/keyword-based plugins only (see module docstring
# for why the two entropy-based plugins are excluded).
_PLUGINS_USED = [
    {"name": "ArtifactoryDetector"},
    {"name": "AWSKeyDetector"},
    {"name": "AzureStorageKeyDetector"},
    {"name": "BasicAuthDetector"},
    {"name": "CloudantDetector"},
    {"name": "DiscordBotTokenDetector"},
    {"name": "GitHubTokenDetector"},
    {"name": "GitLabTokenDetector"},
    {"name": "IbmCloudIamDetector"},
    {"name": "IbmCosHmacDetector"},
    {"name": "IPPublicDetector"},
    {"name": "JwtTokenDetector"},
    {"name": "MailchimpDetector"},
    {"name": "NpmDetector"},
    {"name": "OpenAIDetector"},
    {"name": "PrivateKeyDetector"},
    {"name": "PypiTokenDetector"},
    {"name": "SendGridDetector"},
    {"name": "SlackDetector"},
    {"name": "SoftlayerDetector"},
    {"name": "SquareOAuthDetector"},
    {"name": "StripeDetector"},
    {"name": "TelegramBotTokenDetector"},
    {"name": "TwilioKeyDetector"},
]

# PrivateKeyDetector hits (SSH/PEM/certificates) are always CRITICAL; the
# rest are still real leaked credentials, just slightly lower confidence.
_CRITICAL_TYPES = {"Private Key", "AWS Access Key"}


def detect_secrets_in_text(text: str) -> DetectionResult:
    try:
        from detect_secrets.settings import transient_settings
        from detect_secrets.core.scan import scan_line
    except Exception as exc:
        logger.warning("detect-secrets unavailable: %s", exc)
        return DetectionResult(
            detector="secrets",
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason="detect-secrets library unavailable.",
        )

    matches: list[Match] = []
    hit_types: set[str] = set()
    highest_severity = Severity.NONE
    total_score = 0

    with transient_settings({"plugins_used": _PLUGINS_USED}):
        for line in text.splitlines():
            if not line.strip():
                continue
            for secret in scan_line(line):
                severity = Severity.CRITICAL if secret.type in _CRITICAL_TYPES else Severity.HIGH
                score = 45 if severity == Severity.CRITICAL else 35

                matches.append(
                    Match(label=secret.type, value_preview=f"hash:{secret.secret_hash[:12]}...", start=None, end=None)
                )
                hit_types.add(secret.type)
                total_score += score
                if SEVERITY_RANK[severity] > SEVERITY_RANK[highest_severity]:
                    highest_severity = severity

    total_score = min(total_score, 100)

    if not matches:
        return DetectionResult(
            detector="secrets",
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason="No secrets detected.",
        )

    recommendation = Recommendation.BLOCK if highest_severity == Severity.CRITICAL else Recommendation.REDACT

    return DetectionResult(
        detector="secrets",
        severity=highest_severity,
        score=total_score,
        matches=matches,
        recommendation=recommendation,
        reason=f"detect-secrets found: {', '.join(sorted(hit_types))}.",
    )
