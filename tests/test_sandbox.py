"""Tests for the Sandbox Verification System."""

import pytest

pytest.importorskip("httpx", reason="Sandbox tests require httpx: pip install agentdna-sdk[discovery]")

from agentdna.sandbox.verifier import (
    AgentVerifier,
    CheckResult,
    CheckStatus,
    VerificationLevel,
    VerificationReport,
)


class TestCheckResult:
    def test_pass_result(self):
        r = CheckResult(name="test", status=CheckStatus.PASS, message="OK")
        assert r.to_dict()["status"] == "pass"

    def test_fail_result(self):
        r = CheckResult(name="test", status=CheckStatus.FAIL, message="Failed")
        assert r.to_dict()["status"] == "fail"

    def test_to_dict(self):
        r = CheckResult(
            name="test",
            status=CheckStatus.PASS,
            message="OK",
            details={"key": "value"},
            duration_ms=42.5,
        )
        d = r.to_dict()
        assert d["name"] == "test"
        assert d["duration_ms"] == 42.5


class TestVerificationReport:
    def test_pass_count(self):
        report = VerificationReport(
            agent_id="test",
            level=VerificationLevel.REGISTERED,
            passed=True,
            score=85,
            checks=[
                CheckResult("a", CheckStatus.PASS, "ok"),
                CheckResult("b", CheckStatus.PASS, "ok"),
                CheckResult("c", CheckStatus.FAIL, "bad"),
            ],
        )
        assert report.pass_count == 2
        assert report.fail_count == 1
        assert report.warn_count == 0

    def test_to_dict(self):
        report = VerificationReport(
            agent_id="test",
            level=VerificationLevel.AGENTDNA_VERIFIED,
            passed=True,
            score=95,
        )
        d = report.to_dict()
        assert d["level_name"] == "AGENTDNA_VERIFIED"
        assert d["score"] == 95


class TestAgentVerifier:
    def test_check_agent_card_valid(self):
        verifier = AgentVerifier()
        card = {
            "name": "TestAgent",
            "version": "1.0.0",
            "description": "A test agent",
            "protocol": "a2a",
            "endpoint": "https://test.example.com/a2a",
            "capabilities": [{"skill": "test", "inputs": ["text/plain"]}],
        }
        result = verifier._check_agent_card_valid(card)
        assert result.status == CheckStatus.PASS

    def test_check_agent_card_invalid(self):
        verifier = AgentVerifier()
        card = {
            "name": "TestAgent",
            # missing version, description, protocol, endpoint, capabilities
        }
        result = verifier._check_agent_card_valid(card)
        assert result.status == CheckStatus.FAIL
        assert any("Missing required field" in e for e in result.details["errors"])

    def test_check_agent_card_no_capabilities(self):
        verifier = AgentVerifier()
        card = {
            "name": "TestAgent",
            "version": "1.0.0",
            "description": "A test agent",
            "protocol": "a2a",
            "endpoint": "https://test.example.com/a2a",
            "capabilities": [],
        }
        result = verifier._check_agent_card_valid(card)
        assert result.status == CheckStatus.FAIL
        assert any("No capabilities" in e for e in result.details["errors"])

    def test_check_https_valid(self):
        verifier = AgentVerifier()
        result = verifier._check_https("https://example.com/a2a")
        assert result.status == CheckStatus.PASS

    def test_check_https_invalid(self):
        verifier = AgentVerifier()
        result = verifier._check_https("http://example.com/a2a")
        assert result.status == CheckStatus.FAIL

    def test_check_https_unknown(self):
        verifier = AgentVerifier()
        result = verifier._check_https("ftp://example.com")
        assert result.status == CheckStatus.WARN

    def test_check_agent_card_nested(self):
        """Should handle both nested (agent: {...}) and flat formats."""
        verifier = AgentVerifier()
        nested_card = {
            "agent": {
                "name": "NestedAgent",
                "version": "1.0.0",
                "description": "Nested",
                "protocol": "a2a",
                "endpoint": "https://n.example.com/a2a",
                "capabilities": [{"skill": "test"}],
            }
        }
        result = verifier._check_agent_card_valid(nested_card)
        assert result.status == CheckStatus.PASS
