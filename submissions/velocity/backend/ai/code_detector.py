"""
Source Code Detector - heuristic, signature-based detection of whether a
prompt contains source code, and a best-effort guess at which language.
Deliberately avoids a heavyweight ML model: for the languages we need to
support, a weighted keyword/pattern signature is fast and accurate enough,
and never blocks the pipeline on a missing dependency.
"""
import json
import re

import yaml

from schemas.detection import DetectionResult, Match, Recommendation, Severity

# (language, [signature patterns], min signals required to count as a hit)
_SIGNATURES: dict[str, list[re.Pattern]] = {
    "Python": [
        re.compile(r"^\s*def\s+\w+\s*\("), re.compile(r"^\s*import\s+\w+"), re.compile(r"^\s*from\s+\w+\s+import"),
        re.compile(r"^\s*class\s+\w+.*:\s*$"), re.compile(r"\bself\."), re.compile(r"^\s*#.*"),
        re.compile(r"print\("),
    ],
    "TypeScript": [
        re.compile(r"\binterface\s+\w+\s*\{"), re.compile(r":\s*(string|number|boolean|void|any)\b"),
        re.compile(r"\bexport\s+(default\s+)?(function|class|const)\b"), re.compile(r"=>\s*\{?"),
    ],
    "JavaScript": [
        re.compile(r"\bfunction\s+\w*\s*\("), re.compile(r"\b(const|let|var)\s+\w+\s*="),
        re.compile(r"console\.log\("), re.compile(r"=>\s*\{?"), re.compile(r"\brequire\("),
    ],
    "Java": [
        re.compile(r"\bpublic\s+(static\s+)?(class|void|int|String)\b"), re.compile(r"System\.out\.println\("),
        re.compile(r"\bpublic\s+static\s+void\s+main\s*\("), re.compile(r"\bnew\s+\w+\s*\("),
    ],
    "C++": [
        re.compile(r"#include\s*<\w+>"), re.compile(r"\bstd::\w+"), re.compile(r"\bcout\s*<<"),
        re.compile(r"\bnamespace\s+\w+"),
    ],
    "C": [
        re.compile(r"#include\s*<\w+\.h>"), re.compile(r"\bint\s+main\s*\("), re.compile(r"\bprintf\s*\("),
        re.compile(r";\s*$"),
    ],
    "SQL": [
        re.compile(r"(?i)\bSELECT\b.+\bFROM\b"), re.compile(r"(?i)\bINSERT\s+INTO\b"),
        re.compile(r"(?i)\bCREATE\s+TABLE\b"), re.compile(r"(?i)\bWHERE\b"), re.compile(r"(?i)\bUPDATE\b.+\bSET\b"),
    ],
    "HTML": [
        re.compile(r"<!DOCTYPE html>", re.I), re.compile(r"</?(div|span|html|body|head)[ >]", re.I),
        re.compile(r"<\w+[^>]*>.*</\w+>"),
    ],
    "CSS": [
        re.compile(r"[\.#]?[\w-]+\s*\{[^}]*:[^}]*;[^}]*\}"), re.compile(r"(?i)\b(color|margin|padding|display)\s*:"),
    ],
}


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return False
    try:
        json.loads(stripped)
        return True
    except Exception:
        return False


def _looks_like_yaml(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped.startswith("{") or stripped.startswith("["):
        return False
    if not re.search(r"^\s*[\w.\-]+:\s*.+$", stripped, re.MULTILINE):
        return False
    try:
        parsed = yaml.safe_load(stripped)
        return isinstance(parsed, (dict, list))
    except Exception:
        return False


def detect_source_code(text: str) -> DetectionResult:
    if _looks_like_json(text):
        return _result("JSON", 1.0, [])
    if _looks_like_yaml(text):
        return _result("YAML", 0.7, [])

    scores: dict[str, int] = {}
    for language, patterns in _SIGNATURES.items():
        hits = sum(1 for p in patterns if p.search(text))
        if hits >= 2:
            scores[language] = hits

    if not scores:
        return DetectionResult(
            detector="source_code",
            severity=Severity.NONE,
            score=0,
            matches=[],
            recommendation=Recommendation.ALLOW,
            reason="No source code detected.",
        )

    best_language = max(scores, key=lambda lang: scores[lang])
    confidence = min(scores[best_language] / 5, 1.0)
    return _result(best_language, confidence, [])


def _result(language: str, confidence: float, extra_matches: list[Match]) -> DetectionResult:
    score = min(int(35 * confidence) + 10, 60)
    severity = Severity.MEDIUM if confidence >= 0.5 else Severity.LOW
    return DetectionResult(
        detector="source_code",
        severity=severity,
        score=score,
        matches=[Match(label=language, value_preview=f"{language} code detected", start=None, end=None)] + extra_matches,
        recommendation=Recommendation.WARN,
        reason=f"Prompt appears to contain {language} source code (confidence {confidence:.0%}).",
    )
