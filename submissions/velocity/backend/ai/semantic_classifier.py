"""
OpenRouter Semantic Risk Classifier - the last line of defense, and the
only detector in the pipeline that costs money/latency. It is deliberately
NOT run on every prompt: ai/pipeline.py only calls this when the
deterministic detectors (regex, Presidio, spaCy, source code, keywords,
secrets) are inconclusive - i.e. they found *something* but nothing severe
enough to already decide BLOCK/REDACT, and nothing clearly benign either.

Uses OpenRouter's free-tier models only, tried in order until one responds
successfully. If OPENROUTER_API_KEY isn't configured (Milestone 1/2 default
in a fresh checkout), this fails open with a neutral result instead of
raising - a missing optional API key must never block an employee's prompt.
"""
import json
import logging

import httpx

from config.settings import get_settings
from schemas.detection import DetectionResult, Match, Recommendation, Severity

logger = logging.getLogger("promptshield.ai.semantic")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free-tier model slugs, tried in this order. OpenRouter's free catalog
# changes over time - update this list from https://openrouter.ai/models
# (filter: prompt pricing = free) if a model here gets deprecated.
FREE_MODELS = [
    "deepseek/deepseek-chat-v3.1:free",
    "qwen/qwen3-235b-a22b:free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

_SYSTEM_PROMPT = (
    "You are a corporate AI-usage security classifier. Given a user's prompt to an "
    "AI assistant, decide whether it poses a data-leak or policy risk to the user's "
    "employer. Respond with ONLY a compact JSON object: "
    '{"risk": "LOW"|"MEDIUM"|"HIGH"|"CRITICAL", "reason": "<one sentence>", '
    '"suggested_action": "ALLOW"|"WARN"|"REDACT"|"BLOCK"}. No prose, no markdown fences.'
)

_RISK_TO_SEVERITY = {
    "LOW": Severity.LOW,
    "MEDIUM": Severity.MEDIUM,
    "HIGH": Severity.HIGH,
    "CRITICAL": Severity.CRITICAL,
}
_RISK_TO_SCORE = {"LOW": 10, "MEDIUM": 30, "HIGH": 55, "CRITICAL": 80}


def should_run_semantic_classifier(prior_results: list[DetectionResult]) -> bool:
    """
    Only call OpenRouter when traditional detectors can't confidently
    classify the prompt: nothing already demands BLOCK, but at least one
    detector found *something* worth a second opinion (i.e. it's not an
    obviously clean prompt either).
    """
    if any(r.recommendation == Recommendation.BLOCK for r in prior_results):
        return False  # already confidently decided - don't spend a call
    return any(r.severity != Severity.NONE for r in prior_results)


def classify_semantic_risk(text: str) -> DetectionResult:
    settings = get_settings()
    if not settings.OPENROUTER_API_KEY:
        return DetectionResult(
            detector="semantic",
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason="OPENROUTER_API_KEY not configured - semantic classification skipped.",
        )

    for model in FREE_MODELS:
        try:
            result = _call_model(model, text, settings.OPENROUTER_API_KEY)
            if result is not None:
                return result
        except Exception as exc:
            logger.warning("OpenRouter model %s failed: %s", model, exc)
            continue

    return DetectionResult(
        detector="semantic",
        severity=Severity.NONE,
        score=0,
        matches=[],
        recommendation=Recommendation.ALLOW,
        reason="All OpenRouter free models were unavailable - failing open.",
    )


def _call_model(model: str, text: str, api_key: str) -> DetectionResult | None:
    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text[:4000]},
            ],
            "temperature": 0,
        },
        timeout=15,
    )
    if response.status_code != 200:
        logger.warning("OpenRouter %s returned HTTP %s", model, response.status_code)
        return None

    body = response.json()
    content = body["choices"][0]["message"]["content"].strip()
    content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    parsed = json.loads(content)

    risk = str(parsed.get("risk", "LOW")).upper()
    severity = _RISK_TO_SEVERITY.get(risk, Severity.LOW)
    score = _RISK_TO_SCORE.get(risk, 10)
    reason = parsed.get("reason", "Semantic classifier flagged this prompt.")
    suggested_action = str(parsed.get("suggested_action", "ALLOW")).upper()
    recommendation = (
        Recommendation(suggested_action) if suggested_action in Recommendation.__members__ else Recommendation.WARN
    )

    return DetectionResult(
        detector="semantic",
        severity=severity,
        score=score,
        matches=[Match(label="SEMANTIC_RISK", value_preview=f"model:{model}", start=None, end=None)],
        recommendation=recommendation,
        reason=f"[{model}] {reason}",
    )
