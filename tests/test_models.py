"""Tests for AgentDNA models."""

import pytest

from agentdna.models import Agent, AgentSearchResult, Capability, Pricing, TaskResult, TrustScore


# --- Pricing ---

class TestPricing:
    def test_free_pricing(self):
        p = Pricing(model="free", amount=0)
        assert p.display() == "Free"

    def test_per_minute_usd(self):
        p = Pricing(model="per_minute", amount=0.02, currency="USD")
        assert p.display() == "$0.02/min"

    def test_per_call_eur(self):
        p = Pricing(model="per_call", amount=1.50, currency="EUR")
        assert p.display() == "€1.50/call"

    def test_per_token_gbp(self):
        p = Pricing(model="per_token", amount=0.003, currency="GBP")
        assert p.display() == "£0.00/1K tokens"

    def test_per_item_cny(self):
        p = Pricing(model="per_item", amount=5.00, currency="CNY")
        assert p.display() == "¥5.00/item"

    def test_unknown_currency(self):
        p = Pricing(model="per_call", amount=2.0, currency="BTC")
        assert "BTC" in p.display()

    def test_unknown_model(self):
        p = Pricing(model="per_hour", amount=10.0, currency="USD")
        assert p.display() == "$10.00"


# --- TrustScore ---

class TestTrustScore:
    def test_exceptional_tier(self):
        ts = TrustScore(total=95)
        assert "Exceptional" in ts.tier

    def test_excellent_tier(self):
        ts = TrustScore(total=80)
        assert "Excellent" in ts.tier

    def test_good_tier(self):
        ts = TrustScore(total=70)
        assert "Good" in ts.tier

    def test_fair_tier(self):
        ts = TrustScore(total=50)
        assert "Fair" in ts.tier

    def test_unverified_tier(self):
        ts = TrustScore(total=20)
        assert "Unverified" in ts.tier

    def test_boundary_90(self):
        ts = TrustScore(total=90)
        assert "Exceptional" in ts.tier

    def test_boundary_75(self):
        ts = TrustScore(total=75)
        assert "Excellent" in ts.tier


# --- Capability ---

class TestCapability:
    def test_capability_creation(self):
        cap = Capability(
            skill="transcribe",
            description="Transcribe audio",
            inputs=["audio/wav"],
            output="text/plain",
            languages=["en", "zh"],
            pricing=Pricing(model="per_minute", amount=0.02),
        )
        assert cap.skill == "transcribe"
        assert cap.languages == ["en", "zh"]
        assert cap.pricing.display() == "$0.02/min"

    def test_capability_defaults(self):
        cap = Capability(skill="test")
        assert cap.description == ""
        assert cap.inputs == []
        assert cap.languages == []
        assert cap.pricing is None


# --- TaskResult ---

class TestTaskResult:
    def test_success(self):
        tr = TaskResult(task_id="123", agent_id="test", status="completed")
        assert tr.success is True

    def test_failure(self):
        tr = TaskResult(task_id="123", agent_id="test", status="failed")
        assert tr.success is False

    def test_pending_not_success(self):
        tr = TaskResult(task_id="123", agent_id="test", status="pending")
        assert tr.success is False

    def test_defaults(self):
        tr = TaskResult(task_id="123", agent_id="test", status="completed")
        assert tr.cost == 0.0
        assert tr.currency == "USD"
        assert tr.error is None


# --- Agent ---

class TestAgent:
    def test_repr_with_score(self):
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

    def test_repr_verified(self):
        agent = Agent(
            id="dna:test:v1",
            name="TestAgent",
            version="1.0.0",
            description="Test",
            protocol="a2a",
            endpoint="https://test.example.com/a2a",
            verified=True,
        )
        assert "🏆" in repr(agent)

    def test_repr_no_score(self):
        agent = Agent(
            id="dna:test:v1",
            name="TestAgent",
            version="1.0.0",
            description="Test",
            protocol="mcp",
            endpoint="https://test.example.com/mcp",
        )
        assert "TestAgent" in repr(agent)


# --- AgentSearchResult ---

class TestAgentSearchResult:
    def test_best_with_agents(self):
        agents = [
            Agent(id="1", name="A", version="1.0", description="", protocol="a2a", endpoint="https://a.com", trust_score=TrustScore(total=70)),
            Agent(id="2", name="B", version="1.0", description="", protocol="a2a", endpoint="https://b.com", trust_score=TrustScore(total=90)),
        ]
        result = AgentSearchResult(agents=agents, total=2)
        best = result.best()
        assert best.name == "B"

    def test_best_empty(self):
        result = AgentSearchResult(agents=[], total=0)
        assert result.best() is None

    def test_best_no_scores(self):
        agents = [
            Agent(id="1", name="A", version="1.0", description="", protocol="a2a", endpoint="https://a.com"),
        ]
        result = AgentSearchResult(agents=agents, total=1)
        best = result.best()
        assert best.name == "A"
