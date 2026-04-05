"""Tests for AgentDNA models."""

import pytest

from agentdna.models import Agent, Capability, Pricing, TaskResult, TrustScore


class TestPricing:
    def test_free_pricing(self):
        p = Pricing(model="free", amount=0)
        assert p.display() == "Free"

    def test_per_minute_pricing(self):
        p = Pricing(model="per_minute", amount=0.02, currency="USD")
        assert p.display() == "$0.02/min"

    def test_per_call_pricing(self):
        p = Pricing(model="per_call", amount=1.50, currency="EUR")
        assert p.display() == "€1.50/call"


class TestTrustScore:
    def test_exceptional_tier(self):
        ts = TrustScore(total=95)
        assert "Exceptional" in ts.tier

    def test_good_tier(self):
        ts = TrustScore(total=70)
        assert "Good" in ts.tier

    def test_unverified_tier(self):
        ts = TrustScore(total=20)
        assert "Unverified" in ts.tier


class TestTaskResult:
    def test_success(self):
        tr = TaskResult(task_id="123", agent_id="test", status="completed")
        assert tr.success is True

    def test_failure(self):
        tr = TaskResult(task_id="123", agent_id="test", status="failed")
        assert tr.success is False


class TestAgent:
    def test_repr(self):
        agent = Agent(
            id="dna:test:v1",
            name="TestAgent",
            version="1.0.0",
            description="A test agent",
            protocol="a2a",
            endpoint="https://test.example.com/a2a",
            trust_score=TrustScore(total=85),
        )
        assert "TestAgent" in repr(agent)
        assert "85" in repr(agent)
