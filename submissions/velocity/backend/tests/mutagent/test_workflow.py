"""
Tests for workflow execution — parallel stage, timeout, skipped analyzers,
and error isolation.
"""
import pytest
import time
from unittest.mock import MagicMock, patch

from mutagent.models import (
    AnalyzerResult,
    AnalyzerStatus,
    InvestigationContext,
    DEFAULT_RISK_WEIGHTS,
)
from mutagent.workflow import WORKFLOW, Stage
from schemas.detection import Recommendation, Severity


def _make_ctx(prompt="hello"):
    class MockUser:
        id = "u1"; email = "a@b.com"; full_name = "A"
    class MockSettings:
        allowed_file_types = ["pdf"]; risk_weights = None; enabled_analyzers = None
    return InvestigationContext(
        scan_id="wf-test",
        user=MockUser(),
        browser="ChatGPT",
        raw_prompt=prompt,
        uploaded_files=[],
        keywords=[],
        policies=[],
        org_settings=MockSettings(),
        risk_weights=dict(DEFAULT_RISK_WEIGHTS),
        enabled_analyzers=set(),
        prompt=prompt,
    )


def _make_engine(db=None):
    from mutagent.engine import InvestigationEngine
    engine = InvestigationEngine.__new__(InvestigationEngine)
    engine.db = db or MagicMock()
    engine._registry = {}
    return engine


class TestWorkflowDefinition:
    def test_workflow_has_five_stages(self):
        assert len(WORKFLOW) == 5

    def test_context_stage_is_sequential(self):
        context_stage = WORKFLOW[0]
        assert context_stage.name == "context"
        assert not context_stage.parallel

    def test_analysis_stage_is_parallel(self):
        analysis_stage = next(s for s in WORKFLOW if s.name == "analysis")
        assert analysis_stage.parallel
        assert len(analysis_stage.analyzers) == 4

    def test_decision_stage_is_last(self):
        assert WORKFLOW[-1].name == "decision"


class TestEngineSkipsDisabledAnalyzers:
    def test_skips_disabled_analyzer(self):
        from mutagent.engine import InvestigationEngine
        from mutagent.analyzers.pii_analyzer import PiiAnalyzer

        engine = _make_engine()
        engine._registry = {"PiiAnalyzer": PiiAnalyzer}
        ctx = _make_ctx()
        ctx.enabled_analyzers = {"SecretsAnalyzer"}  # PiiAnalyzer disabled

        engine._run_one(ctx, "PiiAnalyzer")

        assert "PiiAnalyzer" in ctx.analyzer_results
        assert ctx.analyzer_results["PiiAnalyzer"].status == AnalyzerStatus.SKIPPED

    def test_skipped_appears_in_timeline(self):
        from mutagent.engine import InvestigationEngine
        from mutagent.analyzers.pii_analyzer import PiiAnalyzer
        from mutagent.models import TimelineEventType

        engine = _make_engine()
        engine._registry = {"PiiAnalyzer": PiiAnalyzer}
        ctx = _make_ctx()
        ctx.enabled_analyzers = {"SecretsAnalyzer"}

        engine._run_one(ctx, "PiiAnalyzer")

        skipped_events = [e for e in ctx.timeline
                          if e.event_type == TimelineEventType.ANALYZER_SKIPPED]
        assert len(skipped_events) == 1


class TestEngineErrorIsolation:
    def test_failing_analyzer_continues_investigation(self):
        from mutagent.engine import InvestigationEngine
        from mutagent.analyzers.base import BaseAnalyzer

        class BrokenAnalyzer(BaseAnalyzer):
            name = "BrokenAnalyzer"
            display_name = "Broken Agent"
            def run(self, context):
                raise RuntimeError("Simulated failure")

        engine = _make_engine()
        engine._registry = {"BrokenAnalyzer": BrokenAnalyzer}
        ctx = _make_ctx()

        # Should not raise
        engine._run_one(ctx, "BrokenAnalyzer")

        assert "BrokenAnalyzer" in ctx.analyzer_results
        assert ctx.analyzer_results["BrokenAnalyzer"].status == AnalyzerStatus.FAILED


class TestParallelExecution:
    def test_parallel_analyzers_all_run(self):
        from mutagent.engine import InvestigationEngine
        from mutagent.analyzers.pii_analyzer import PiiAnalyzer
        from mutagent.analyzers.secrets_analyzer import SecretsAnalyzer
        from mutagent.analyzers.injection_analyzer import InjectionAnalyzer
        from mutagent.analyzers.compliance_analyzer import ComplianceAnalyzer

        engine = _make_engine()
        engine._registry = {
            "PiiAnalyzer": PiiAnalyzer,
            "SecretsAnalyzer": SecretsAnalyzer,
            "InjectionAnalyzer": InjectionAnalyzer,
            "ComplianceAnalyzer": ComplianceAnalyzer,
        }
        ctx = _make_ctx("hello world")
        stage = Stage(
            name="analysis",
            analyzers=["PiiAnalyzer", "SecretsAnalyzer", "InjectionAnalyzer", "ComplianceAnalyzer"],
            parallel=True,
        )
        engine._run_parallel(ctx, stage)

        for name in ["PiiAnalyzer", "SecretsAnalyzer", "InjectionAnalyzer", "ComplianceAnalyzer"]:
            assert name in ctx.analyzer_results
