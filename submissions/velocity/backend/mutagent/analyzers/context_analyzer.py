"""
ContextAnalyzer — Stage 1 of the investigation workflow.

Responsibility: normalize the raw prompt text and populate context.prompt.
No detection, no evidence, no database writes.

This runs synchronously before any other analyzer so every subsequent
analyzer receives a clean, normalized text to work with.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mutagent.analyzers.base import BaseAnalyzer
from mutagent.models import AnalyzerResult, AnalyzerStatus, Evidence
from schemas.detection import Recommendation, Severity

if TYPE_CHECKING:
    from mutagent.models import InvestigationContext

logger = logging.getLogger("promptshield.mutagent.context_analyzer")


class ContextAnalyzer(BaseAnalyzer):
    """
    Collects and normalizes investigation context.

    Sets context.prompt (the normalized text that all other analyzers use).
    Records user, browser/target_ai, file metadata — no detection.
    """
    name = "ContextAnalyzer"
    display_name = "Context Agent"
    timeout_seconds = 1.0

    def run(self, context: "InvestigationContext") -> AnalyzerResult:
        start = self._start_timer()
        try:
            from ai.normalizer import normalize_prompt
            normalized = normalize_prompt(context.raw_prompt)
            context.prompt = normalized.normalized

            elapsed = self._elapsed_ms(start)
            summary = (
                f"Context established: user={context.user.email}, "
                f"target={context.browser}, "
                f"prompt_length={len(context.prompt)}, "
                f"files={len(context.uploaded_files)}"
            )
            logger.debug(summary)

            return AnalyzerResult(
                agent_name=self.name,
                display_name=self.display_name,
                status=AnalyzerStatus.SUCCESS,
                execution_time_ms=elapsed,
                confidence=1.0,
                severity=Severity.NONE,
                findings=[],
                evidence=[
                    Evidence(
                        label="INVESTIGATION_CONTEXT",
                        value_preview=(
                            f"user={context.user.email} | "
                            f"target={context.browser} | "
                            f"files={len(context.uploaded_files)}"
                        ),
                        confidence=1.0,
                        location="system",
                        detector="context",
                        severity=Severity.NONE,
                        metadata={
                            "user_id": context.user.id,
                            "user_email": context.user.email,
                            "target_ai": context.browser,
                            "prompt_length": len(context.prompt),
                            "file_count": len(context.uploaded_files),
                            "file_names": [f.filename for f in context.uploaded_files],
                        },
                    )
                ],
                recommendation=Recommendation.ALLOW,
                summary=summary,
            )
        except Exception as exc:
            logger.exception("ContextAnalyzer failed")
            # Fallback: use raw prompt unchanged so the investigation can continue
            context.prompt = context.raw_prompt
            return self._failed(str(exc), self._elapsed_ms(start))
