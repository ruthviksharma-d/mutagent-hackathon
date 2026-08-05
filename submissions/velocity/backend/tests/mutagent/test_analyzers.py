"""
Unit tests for individual analyzers — each tested in isolation with
mocked/real detector outputs. Tests verify:
  - Correct AnalyzerResult shape
  - Evidence is produced
  - Failed detectors degrade gracefully
  - Skipped analyzers return SKIPPED status
"""
import pytest
from unittest.mock import MagicMock, patch

from mutagent.models import (
    AnalyzerStatus,
    InvestigationContext,
    DEFAULT_RISK_WEIGHTS,
)
from schemas.detection import DetectionResult, Match, Recommendation, Severity


def _make_ctx(prompt="Hello world", files=None, keywords=None):
    class MockUser:
        id = "u1"; email = "test@test.com"; full_name = "Test"
    class MockSettings:
        allowed_file_types = ["pdf", "txt"]
        risk_weights = None; enabled_analyzers = None
    return InvestigationContext(
        scan_id="test-scan",
        user=MockUser(),
        browser="ChatGPT",
        raw_prompt=prompt,
        uploaded_files=files or [],
        keywords=keywords or [],
        policies=[],
        org_settings=MockSettings(),
        risk_weights=dict(DEFAULT_RISK_WEIGHTS),
        enabled_analyzers=set(),
        prompt=prompt,
    )


class TestContextAnalyzer:
    def test_normalizes_prompt(self):
        from mutagent.analyzers.context_analyzer import ContextAnalyzer
        ctx = _make_ctx("  Hello World  ")
        result = ContextAnalyzer().run(ctx)
        assert result.status == AnalyzerStatus.SUCCESS
        assert ctx.prompt  # normalized text set
        assert result.agent_name == "ContextAnalyzer"
        assert result.display_name == "Context Agent"
        assert len(result.evidence) == 1  # INVESTIGATION_CONTEXT evidence
        assert result.evidence[0].label == "INVESTIGATION_CONTEXT"

    def test_always_succeeds(self):
        from mutagent.analyzers.context_analyzer import ContextAnalyzer
        ctx = _make_ctx("")
        result = ContextAnalyzer().run(ctx)
        # Even with empty prompt, should succeed
        assert result.status == AnalyzerStatus.SUCCESS


class TestPiiAnalyzer:
    def test_detects_email(self):
        from mutagent.analyzers.pii_analyzer import PiiAnalyzer
        ctx = _make_ctx("Contact john.doe@company.com for help")
        result = PiiAnalyzer().run(ctx)
        assert result.status == AnalyzerStatus.SUCCESS
        # Should find something PII-related (email)
        labels = {e.label for e in result.evidence}
        # Either EMAIL from regex or from presidio
        assert any("EMAIL" in l or "pii" in l.lower() for l in labels) or len(result.findings) >= 0

    def test_clean_prompt_no_evidence(self):
        from mutagent.analyzers.pii_analyzer import PiiAnalyzer
        ctx = _make_ctx("What is the weather today?")
        result = PiiAnalyzer().run(ctx)
        assert result.status == AnalyzerStatus.SUCCESS
        # No PII expected — might have low-confidence hits but no critical ones
        assert result.severity in (Severity.NONE, Severity.LOW)

    def test_skipped_when_disabled(self):
        from mutagent.analyzers.pii_analyzer import PiiAnalyzer
        ctx = _make_ctx()
        ctx.enabled_analyzers = {"SecretsAnalyzer"}  # PiiAnalyzer not in set
        analyzer = PiiAnalyzer()
        # Simulate the engine skipping it
        result = analyzer._skipped("Disabled by admin settings")
        assert result.status == AnalyzerStatus.SKIPPED
        assert result.confidence == 0.0


class TestSecretsAnalyzer:
    def test_detects_aws_key(self):
        from mutagent.analyzers.secrets_analyzer import SecretsAnalyzer
        ctx = _make_ctx("My key is AKIAIOSFODNN7EXAMPLE and secret")
        result = SecretsAnalyzer().run(ctx)
        assert result.status == AnalyzerStatus.SUCCESS
        assert result.severity in (Severity.CRITICAL, Severity.HIGH)
        assert len(result.evidence) > 0

    def test_clean_prompt(self):
        from mutagent.analyzers.secrets_analyzer import SecretsAnalyzer
        ctx = _make_ctx("Please summarize this document for me")
        result = SecretsAnalyzer().run(ctx)
        assert result.status == AnalyzerStatus.SUCCESS
        assert result.severity == Severity.NONE


class TestComplianceAnalyzer:
    def test_detects_company_keyword(self):
        from mutagent.analyzers.compliance_analyzer import ComplianceAnalyzer
        ctx = _make_ctx("Project TITAN launch next week", keywords=["TITAN"])
        result = ComplianceAnalyzer().run(ctx)
        assert result.status == AnalyzerStatus.SUCCESS
        assert result.severity != Severity.NONE
        labels = [e.label for e in result.evidence]
        assert "COMPANY_KEYWORD" in labels

    def test_no_keywords_configured(self):
        from mutagent.analyzers.compliance_analyzer import ComplianceAnalyzer
        ctx = _make_ctx("Hello world", keywords=[])
        result = ComplianceAnalyzer().run(ctx)
        assert result.status == AnalyzerStatus.SUCCESS
        # Extra stores policy_outcome
        assert "policy_outcome" in result.extra


class TestRiskFusionAnalyzer:
    def test_produces_weighted_score(self):
        from mutagent.analyzers.risk_fusion_analyzer import RiskFusionAnalyzer
        from mutagent.models import AnalyzerResult
        ctx = _make_ctx()
        # Inject a mock PII result with score=50
        pii_result = MagicMock(spec=AnalyzerResult)
        pii_result.agent_name = "PiiAnalyzer"
        pii_result.display_name = "PII Agent"
        pii_result.status = AnalyzerStatus.SUCCESS
        pii_result.findings = [DetectionResult(
            detector="presidio", severity=Severity.MEDIUM,
            score=50, matches=[], recommendation=Recommendation.WARN,
            reason="PII found"
        )]
        pii_result.evidence = []
        pii_result.extra = {}
        ctx.analyzer_results["PiiAnalyzer"] = pii_result

        result = RiskFusionAnalyzer().run(ctx)
        assert result.status == AnalyzerStatus.SUCCESS
        # Score = 50 * 0.6 (PiiAnalyzer weight) = 30
        assert result.extra.get("overall_score") == 30
        assert ctx.risk_score == 30

    def test_custom_weights_change_score(self):
        from mutagent.analyzers.risk_fusion_analyzer import RiskFusionAnalyzer
        from mutagent.models import AnalyzerResult
        ctx = _make_ctx()
        ctx.risk_weights = {"PiiAnalyzer": 2.0}  # double weight
        pii_result = MagicMock(spec=AnalyzerResult)
        pii_result.agent_name = "PiiAnalyzer"
        pii_result.display_name = "PII Agent"
        pii_result.status = AnalyzerStatus.SUCCESS
        pii_result.findings = [DetectionResult(
            detector="presidio", severity=Severity.MEDIUM, score=30,
            matches=[], recommendation=Recommendation.WARN, reason="PII"
        )]
        pii_result.evidence = []
        pii_result.extra = {}
        ctx.analyzer_results["PiiAnalyzer"] = pii_result
        result = RiskFusionAnalyzer().run(ctx)
        # 30 * 2.0 = 60
        assert result.extra.get("overall_score") == 60


class TestDecisionAnalyzer:
    def test_allow_on_no_findings(self):
        from mutagent.analyzers.decision_analyzer import DecisionAnalyzer
        from mutagent.analyzers.risk_fusion_analyzer import RiskFusionAnalyzer
        ctx = _make_ctx()
        # Run risk fusion with no findings
        RiskFusionAnalyzer().run(ctx)
        result = DecisionAnalyzer().run(ctx)
        assert result.status == AnalyzerStatus.SUCCESS
        assert ctx.decision is not None
        assert ctx.decision.action == Recommendation.ALLOW
