"""
Prompt Normalizer - the first stage of the pipeline. Every downstream
detector operates on the *normalized* text, not the raw prompt, so that
invisible-character obfuscation, inconsistent line endings, and irregular
whitespace can't be used to dodge detection.
"""
import re
import unicodedata

from pydantic import BaseModel

# Zero-width / directional-override / BOM characters sometimes used to split
# up sensitive strings (e.g. "sk-​ABCDEF...") to evade naive regexes.
_INVISIBLE_CHARS_RE = re.compile(
    "[" + "".join([
        "​", "‌", "‍", "‎", "‏",  # zero-width / directional marks
        "‪", "‫", "‬", "‭", "‮",  # bidi overrides
        "﻿",  # BOM
        "⁠",  # word joiner
    ]) + "]"
)
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_BLANK_LINES_RE = re.compile(r"\n{3,}")


class NormalizedPrompt(BaseModel):
    original: str
    normalized: str
    language: str | None
    char_count: int


def normalize_prompt(text: str) -> NormalizedPrompt:
    original = text

    # Unicode-normalize first so composed/decomposed lookalikes collapse
    # to a single canonical form before we strip anything.
    working = unicodedata.normalize("NFKC", text)

    # Standardize line endings.
    working = working.replace("\r\n", "\n").replace("\r", "\n")

    # Strip invisible/zero-width characters used to evade regex matching.
    working = _INVISIBLE_CHARS_RE.sub("", working)

    # Collapse repeated horizontal whitespace and excessive blank lines,
    # but preserve normal paragraph structure.
    working = _MULTI_SPACE_RE.sub(" ", working)
    working = _MULTI_BLANK_LINES_RE.sub("\n\n", working)
    working = working.strip()

    language = _detect_language(working)

    return NormalizedPrompt(
        original=original,
        normalized=working,
        language=language,
        char_count=len(working),
    )


def _detect_language(text: str) -> str | None:
    if len(text.strip()) < 3:
        return None
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0  # deterministic results
        return detect(text)
    except Exception:
        return None
