"""
Tests for trace helper functions — timeline recording, JSON summary shape,
and evidence aggregation.
"""
import pytest
from unittest.mock import MagicMock

from mutagent.models import (
    AnalyzerResult,
    AnalyzerStatus,
    Evidence,
    InvestigationContext,
    DEFAULT_RISK_WEIGHTS,
    TimelineEventType,
)
from mutagent.trace import (
    build_investigation_summary,
    record_investigation_start,
    record_skipped,
    record_start,
    record_finish,
    record_decision,
)
from schemas.detection import Recommendation, Severity


def _make_ctx():
    class MockUser:
        id = "u1"; email = "a@b.com"; full_name = "A"
    class MockSettings:
        allowed_file_types = []; risk_weights = None; enabled_analyzers = None
    return InvestigationContext(
        scan_id="trace-test",
        user=MockUser(),
        browser="Claude",
        raw_prompt="hello",
        uploaded_files=[],
        keywords=[],
        policies=[],
        org_settings=MockSettings(),
        risk_weights=dict(DEFAULT_RISK_WEIGHTS),
        enabled_analyzers=set(),
        prompt="hello",
    )


class TestTimelineRecording:
    def test_record_start_adds_event(self):
        ctx = _make_ctx()
        record_start(ctx, "PiiAnalyzer")
        assert len(ctx.timeline) == 1
        assert ctx.timeline[0].event_type == TimelineEventType.ANALYZER_STARTED
        assert ctx.timeline[0].analyzer_name == "PiiAnalyzer"

    def test_record_skipped_adds_skipped_event(self):
        ctx = _make_ctx()
        record_skipped(ctx, "SecretsAnalyzer", "Disabled")
        assert ctx.timeline[0].event_type == TimelineEventType.ANALYZER_SKIPPED

    def test_record_finish_failed_adds_failed_event(self):
        ctx = _make_ctx()
        failed = AnalyzerResult(
            agent_name="X", display_name="X Agent",
            status=AnalyzerStatus.FAILED, execution_time_ms=10.0,
            confidence=0.0, severity=Severity.NONE,
            findings=[], evidence=[],
            recommendation=Recommendation.ALLOW,
            summary="Failed", error="Something went wrong",
        )
        record_finish(ctx, "X", failed)
        assert ctx.timeline[0].event_type == TimelineEventType.ANALYZER_FAILED

    def test_record_investigation_start(self):
        ctx = _make_ctx()
        record_investigation_start(ctx)
        assert ctx.timeline[0].event_type == TimelineEventType.INVESTIGATION_START


class TestBuildInvestigationSummary:
    def test_summary_is_dict(self):
        ctx = _make_ctx()
        summary = build_investigation_summary(ctx)
        assert isinstance(summary, dict)

    def test_summary_contains_required_keys(self):
        ctx = _make_ctx()
        summary = build_investigation_summary(ctx)
        required_keys = [
            "scan_id", "user", "target_ai", "risk_score",
            "decision", "analyzers", "evidence", "total_execution_ms",
        ]
        for key in required_keys:
            assert key in summary, f"Missing key: {key}"

    def test_summary_aggregates_evidence(self):
        ctx = _make_ctx()
        result = AnalyzerResult(
            agent_name="PiiAnalyzer", display_name="PII Agent",
            status=AnalyzerStatus.SUCCESS, execution_time_ms=50.0,
            confidence=0.9, severity=Severity.LOW,
            findings=[], evidence=[
                Evidence(label="EMAIL", value_preview="j***@x.com",
                         confidence=0.9, location="prompt",
                         detector="presidio", severity=Severity.LOW)
            ],
            recommendation=Recommendation.ALLOW,
            summary="Found email",
        )
        ctx.record_analyzer_result(result)
        summary = build_investigation_summary(ctx)
        assert len(summary["evidence"]) == 1
        assert summary["evidence"][0]["label"] == "EMAIL"

    def test_summary_target_ai(self):
        ctx = _make_ctx()
        summary = build_investigation_summary(ctx)
        assert summary["target_ai"] == "Claude"

    def test_summary_unknown_decision_when_no_decision(self):
        ctx = _make_ctx()
        summary = build_investigation_summary(ctx)
        assert summary["decision"] == "UNKNOWN"
