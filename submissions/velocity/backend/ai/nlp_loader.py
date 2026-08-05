"""
Shared spaCy pipeline loader used by both the spaCy NER Detector and the
Presidio Detector, so the (fairly expensive) model is only loaded into
memory once per process.

The en_core_web_sm model is NOT a pip package - it must be downloaded
separately with `python -m spacy download en_core_web_sm`. If it hasn't
been downloaded yet, every caller of get_nlp() gets None back and degrades
gracefully (see spacy_detector.py / presidio_detector.py) instead of
crashing the scan pipeline.
"""
import logging
from functools import lru_cache

logger = logging.getLogger("promptshield.ai.nlp")

MODEL_NAME = "en_core_web_sm"


@lru_cache
def get_nlp():
    try:
        import spacy

        return spacy.load(MODEL_NAME)
    except Exception as exc:  # OSError if model missing, ImportError if spacy missing
        logger.warning(
            "spaCy model '%s' is not available (%s). "
            "Run `python -m spacy download %s` to enable the spaCy and Presidio detectors.",
            MODEL_NAME,
            exc,
            MODEL_NAME,
        )
        return None


def is_nlp_available() -> bool:
    return get_nlp() is not None
