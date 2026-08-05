"""
InvestigationEngine — the heart of PromptShield's multi-analyzer architecture.

This is the main orchestrator. It:
    1. Builds the InvestigationContext (one DB read upfront)
    2. Executes analyzers according to the WORKFLOW graph
    3. Handles per-analyzer errors and timeouts gracefully
    4. Records a rich timeline of events
    5. Persists the investigation trace to the DB
    6. Returns a PipelineOutput (same type as the old run_pipeline)

Usage (from ai/pipeline.py):
    from mutagent.engine import InvestigationEngine
    output = InvestigationEngine(db).run(user=user, prompt=..., site=..., files=...)

Auto-discovery: on first instantiation, the engine scans
mutagent/analyzers/ for all BaseAnalyzer subclasses and registers them.
Adding a new analyzer requires only creating the file — no engine changes.
"""
from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import TYPE_CHECKING

from mutagent.analyzers.base import BaseAnalyzer
from mutagent.context import build_context
from mutagent.models import (
    AnalyzerResult,
    AnalyzerStatus,
    DEFAULT_ANALYZER_TIMEOUT_SECONDS,
    InvestigationContext,
)
from mutagent.trace import (
    build_investigation_summary,
    persist_trace,
    record_decision,
    record_finish,
    record_investigation_end,
    record_investigation_start,
    record_recovered,
    record_skipped,
    record_start,
)
from mutagent.workflow import WORKFLOW, Stage

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from models.user import User
    from schemas.scan import ScanFileInput

logger = logging.getLogger("promptshield.mutagent.engine")


def _build_registry() -> dict[str, type[BaseAnalyzer]]:
    """
    Auto-discover all BaseAnalyzer subclasses in mutagent/analyzers/.
    Returns a dict mapping class name → class.
    """
    import mutagent.analyzers as analyzers_pkg

    registry: dict[str, type[BaseAnalyzer]] = {}
    for _, module_name, _ in pkgutil.iter_modules(analyzers_pkg.__path__):
        if module_name == "base":
            continue
        try:
            module = importlib.import_module(f"mutagent.analyzers.{module_name}")
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BaseAnalyzer)
                    and obj is not BaseAnalyzer
                    and obj.name  # skip unnamed stubs
                ):
                    registry[obj.name] = obj
                    logger.debug("Registered analyzer: %s", obj.name)
        except Exception:
            logger.exception("Failed to load analyzer module: %s", module_name)

    return registry


# Build once at module level (process lifetime)
_ANALYZER_REGISTRY: dict[str, type[BaseAnalyzer]] = {}


def _get_registry() -> dict[str, type[BaseAnalyzer]]:
    global _ANALYZER_REGISTRY
    if not _ANALYZER_REGISTRY:
        _ANALYZER_REGISTRY = _build_registry()
    return _ANALYZER_REGISTRY


class InvestigationEngine:
    """
    Orchestrates a full multi-analyzer security investigation.

    Each call to .run() is independent — no shared state between calls.
    """

    def __init__(self, db: "Session") -> None:
        self.db = db
        self._registry = _get_registry()

    def run(
        self,
        user: "User",
        prompt: str,
        site: str,
        files: "list[ScanFileInput]",
    ) -> "PipelineOutput":
        """
        Execute a full investigation and return a PipelineOutput.

        This method never raises — all errors are handled internally and
        result in a degraded (but valid) output.
        """
        from ai.pipeline import PipelineOutput

        investigation_start = time.monotonic()

        # Build context (one DB read upfront)
        ctx = build_context(self.db, user, prompt, site, files)
        record_investigation_start(ctx)
        logger.info(
            "Investigation started scan_id=%s user=%s site=%s files=%d",
            ctx.scan_id, user.email, site, len(files),
        )

        # Execute workflow stages
        for stage in WORKFLOW:
            self._run_stage(ctx, stage)

        total_ms = round((time.monotonic() - investigation_start) * 1000, 2)
        record_investigation_end(ctx, total_ms)

        if ctx.decision:
            record_decision(ctx)

        logger.info(
            "Investigation complete scan_id=%s decision=%s score=%d time=%.0fms",
            ctx.scan_id,
            ctx.decision.action.value if ctx.decision else "UNKNOWN",
            ctx.risk_score,
            total_ms,
        )

        # Build and persist trace (never blocks the scan on failure)
        summary = build_investigation_summary(ctx)
        persist_trace(self.db, ctx, summary)

        # Return the same PipelineOutput shape the router expects
        from ai.decision_engine import Decision
        from schemas.detection import Recommendation, Severity
        decision = ctx.decision or Decision(
            risk=Severity.NONE,
            score=0,
            action=Recommendation.ALLOW,
            reason="No decision was produced.",
            triggered_rules=[],
        )

        return PipelineOutput(
            decision=decision,
            sanitized_prompt=ctx.sanitized_prompt or ctx.prompt,
            all_results=ctx.findings,
            file_findings=ctx.file_findings,
        )

    # ------------------------------------------------------------------
    # Stage execution
    # ------------------------------------------------------------------

    def _run_stage(self, ctx: InvestigationContext, stage: Stage) -> None:
        """Run one workflow stage (sequential or parallel)."""
        if stage.parallel:
            self._run_parallel(ctx, stage)
        else:
            for analyzer_name in stage.analyzers:
                self._run_one(ctx, analyzer_name)

    def _run_parallel(self, ctx: InvestigationContext, stage: Stage) -> None:
        """Run a group of analyzers concurrently with per-analyzer timeouts."""
        analyzers_to_run = [
            name for name in stage.analyzers
            if ctx.is_analyzer_enabled(name)
        ]
        skipped = [name for name in stage.analyzers if name not in analyzers_to_run]
        for name in skipped:
            result = self._get_analyzer(name)._skipped("Disabled by admin settings")
            ctx.record_analyzer_result(result)
            record_skipped(ctx, name, "Disabled by admin settings")

        if not analyzers_to_run:
            return

        with ThreadPoolExecutor(max_workers=len(analyzers_to_run)) as executor:
            future_map: dict[str, Future] = {}
            for name in analyzers_to_run:
                analyzer = self._get_analyzer(name)
                if analyzer is None:
                    continue
                record_start(ctx, name)
                future_map[name] = executor.submit(analyzer.run, ctx)

            for name, future in future_map.items():
                analyzer = self._get_analyzer(name)
                timeout = getattr(analyzer, "timeout_seconds", DEFAULT_ANALYZER_TIMEOUT_SECONDS)
                try:
                    result = future.result(timeout=timeout)
                    ctx.record_analyzer_result(result)
                    record_finish(ctx, name, result)
                    if result.status == AnalyzerStatus.FAILED:
                        record_recovered(ctx, name)
                except FuturesTimeout:
                    elapsed_ms = timeout * 1000
                    timeout_result = AnalyzerResult(
                        agent_name=name,
                        display_name=analyzer.display_name if analyzer else name,
                        status=AnalyzerStatus.TIMEOUT,
                        execution_time_ms=elapsed_ms,
                        confidence=0.0,
                        severity=__import__("schemas.detection", fromlist=["Severity"]).Severity.NONE,
                        findings=[],
                        evidence=[],
                        recommendation=__import__("schemas.detection", fromlist=["Recommendation"]).Recommendation.ALLOW,
                        summary=f"{name} timed out after {timeout}s",
                        error=f"Timed out after {timeout}s",
                    )
                    ctx.record_analyzer_result(timeout_result)
                    record_finish(ctx, name, timeout_result)
                    record_recovered(ctx, name)
                    future.cancel()
                except Exception as exc:
                    from schemas.detection import Recommendation, Severity
                    failed_result = AnalyzerResult(
                        agent_name=name,
                        display_name=analyzer.display_name if analyzer else name,
                        status=AnalyzerStatus.FAILED,
                        execution_time_ms=0.0,
                        confidence=0.0,
                        severity=Severity.NONE,
                        findings=[],
                        evidence=[],
                        recommendation=Recommendation.ALLOW,
                        summary=f"{name} raised an unhandled exception: {exc}",
                        error=str(exc),
                    )
                    ctx.record_analyzer_result(failed_result)
                    record_finish(ctx, name, failed_result)
                    record_recovered(ctx, name)
                    logger.exception("Analyzer %s raised unhandled exception", name)

    def _run_one(self, ctx: InvestigationContext, analyzer_name: str) -> None:
        """Run a single analyzer sequentially with graceful error handling."""
        if not ctx.is_analyzer_enabled(analyzer_name):
            analyzer = self._get_analyzer(analyzer_name)
            result = (analyzer or _StubAnalyzer(analyzer_name))._skipped(
                "Disabled by admin settings"
            )
            ctx.record_analyzer_result(result)
            record_skipped(ctx, analyzer_name, "Disabled by admin settings")
            return

        analyzer = self._get_analyzer(analyzer_name)
        if analyzer is None:
            logger.warning("Analyzer not found in registry: %s", analyzer_name)
            return

        record_start(ctx, analyzer_name)
        try:
            result = analyzer.run(ctx)
            ctx.record_analyzer_result(result)
            record_finish(ctx, analyzer_name, result)
            if result.status == AnalyzerStatus.FAILED:
                record_recovered(ctx, analyzer_name)
        except Exception as exc:
            from schemas.detection import Recommendation, Severity
            failed = AnalyzerResult(
                agent_name=analyzer_name,
                display_name=analyzer.display_name,
                status=AnalyzerStatus.FAILED,
                execution_time_ms=0.0,
                confidence=0.0,
                severity=Severity.NONE,
                findings=[],
                evidence=[],
                recommendation=Recommendation.ALLOW,
                summary=f"{analyzer_name} raised: {exc}",
                error=str(exc),
            )
            ctx.record_analyzer_result(failed)
            record_finish(ctx, analyzer_name, failed)
            record_recovered(ctx, analyzer_name)
            logger.exception("Analyzer %s raised unhandled exception", analyzer_name)

    def _get_analyzer(self, name: str) -> BaseAnalyzer | None:
        cls = self._registry.get(name)
        if cls is None:
            logger.warning("No analyzer registered for name: %s", name)
            return None
        return cls()


class _StubAnalyzer(BaseAnalyzer):
    """Placeholder for unknown analyzer names (graceful degradation)."""
    def __init__(self, name: str):
        self.name = name
        self.display_name = name

    def run(self, context):
        return self._skipped("Not found in registry")


# Lazy import to avoid circular deps at module level
def _PipelineOutput():
    from ai.pipeline import PipelineOutput
    return PipelineOutput
