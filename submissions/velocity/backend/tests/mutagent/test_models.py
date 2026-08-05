"""
Unit tests for Mutagent data models.
Tests: InvestigationContext, AnalyzerResult, Evidence, TimelineEvent construction.
"""
import pytest
from datetime import datetime, timezone

from mutagent.models import (
    AnalyzerResult,
    AnalyzerStatus,
    Evidence,
    InvestigationContext,
    TimelineEvent,
    TimelineEventType,
    DEFAULT_RISK_WEIGHTS,
)
from schemas.detection import Recommendation, Severity


def _make_mock_user():
    class MockUser:
        id = "user-1"
        email = "test@company.com"
        full_name = "Test User"
    return MockUser()


def _make_mock_settings():
    class MockSettings:
        allowed_file_types = ["pdf", "txt"]
        risk_weights = None
        enabled_analyzers = None
    return MockSettings()


class TestEvidence:
    def test_to_dict_contains_all_fields(self):
        e = Evidence(
            label="EMAIL",
            value_preview="jo***@company.com",
            confidence=0.99,
            location="prompt",
            detector="presidio",
            severity=Severity.LOW,
            start=0,
            end=20,
        )
        d = e.to_dict()
        assert d["label"] == "EMAIL"
        assert d["confidence"] == 0.99
        assert d["severity"] == "LOW"
        assert d["start"] == 0

    def test_to_dict_with_metadata(self):
        e = Evidence(
            label="POLICY_TRIGGERED",
            value_preview="Policy: Block PII",
            confidence=1.0,
            location="policy_engine",
            detector="policy",
            severity=Severity.HIGH,
            metadata={"policy_id": "p1", "action": "BLOCK"},
        )
        d = e.to_dict()
        assert d["metadata"]["policy_id"] == "p1"


class TestAnalyzerResult:
    def test_to_dict_shape(self):
        result = AnalyzerResult(
            agent_name="PiiAnalyzer",
            display_name="PII Agent",
            status=AnalyzerStatus.SUCCESS,
            execution_time_ms=123.4,
            confidence=0.8,
            severity=Severity.LOW,
            findings=[],
            evidence=[],
            recommendation=Recommendation.WARN,
            summary="Found 1 email.",
        )
        d = result.to_dict()
        assert d["agent_name"] == "PiiAnalyzer"
        assert d["display_name"] == "PII Agent"
        assert d["status"] == "SUCCESS"
        assert d["confidence"] == 0.8


class TestInvestigationContext:
    def test_is_analyzer_enabled_empty_set_means_all(self):
        ctx = InvestigationContext(
            scan_id="test",
            user=_make_mock_user(),
            browser="ChatGPT",
            raw_prompt="hello",
            uploaded_files=[],
            keywords=[],
            policies=[],
            org_settings=_make_mock_settings(),
            risk_weights=dict(DEFAULT_RISK_WEIGHTS),
            enabled_analyzers=set(),  # empty = all
        )
        assert ctx.is_analyzer_enabled("PiiAnalyzer") is True
        assert ctx.is_analyzer_enabled("SecretsAnalyzer") is True

    def test_is_analyzer_enabled_explicit_set(self):
        ctx = InvestigationContext(
            scan_id="test",
            user=_make_mock_user(),
            browser="ChatGPT",
            raw_prompt="hello",
            uploaded_files=[],
            keywords=[],
            policies=[],
            org_settings=_make_mock_settings(),
            risk_weights=dict(DEFAULT_RISK_WEIGHTS),
            enabled_analyzers={"PiiAnalyzer"},
        )
        assert ctx.is_analyzer_enabled("PiiAnalyzer") is True
        assert ctx.is_analyzer_enabled("SecretsAnalyzer") is False

    def test_add_findings_extends_list(self):
        from schemas.detection import DetectionResult
        ctx = InvestigationContext(
            scan_id="test",
            user=_make_mock_user(),
            browser="ChatGPT",
            raw_prompt="hello",
            uploaded_files=[],
            keywords=[],
            policies=[],
            org_settings=_make_mock_settings(),
            risk_weights=dict(DEFAULT_RISK_WEIGHTS),
            enabled_analyzers=set(),
        )
        dr = DetectionResult(
            detector="test", severity=Severity.LOW, score=10,
            matches=[], recommendation=Recommendation.WARN, reason="test"
        )
        ctx.add_findings([dr])
        assert len(ctx.findings) == 1


class TestTimelineEvent:
    def test_to_dict_contains_timestamp(self):
        event = TimelineEvent(
            event_type=TimelineEventType.ANALYZER_STARTED,
            message="PiiAnalyzer started",
            analyzer_name="PiiAnalyzer",
        )
        d = event.to_dict()
        assert d["event_type"] == "analyzer_started"
        assert "timestamp" in d
        assert d["analyzer_name"] == "PiiAnalyzer"

    def test_to_dict_with_duration(self):
        event = TimelineEvent(
            event_type=TimelineEventType.ANALYZER_FINISHED,
            message="Done",
            duration_ms=42.5,
        )
        assert event.to_dict()["duration_ms"] == 42.5
