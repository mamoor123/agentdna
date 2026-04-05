"""Tests for the Registry Server — API endpoints with SQLite persistence."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Use a temp database for tests
_tmpdir = tempfile.mkdtemp()
os.environ["AGENTDNA_REGISTRY_DB_PATH"] = os.path.join(_tmpdir, "test_registry.db")
os.environ["AGENTDNA_DB_PATH"] = os.path.join(_tmpdir, "test_observe.db")

from registry.server import app  # noqa: E402


@pytest.fixture
def client():
    """Create a fresh test client for each test."""
    # Reset the database for each test
    db_path = os.environ["AGENTNA_REGISTRY_DB_PATH"] = os.environ["AGENTDNA_REGISTRY_DB_PATH"]
    if os.path.exists(db_path):
        os.remove(db_path)
    # Re-import storage to pick up fresh db
    from registry import storage
    storage._get_conn()  # ensure tables exist
    return TestClient(app)


SAMPLE_AGENT = {
    "agent": {
        "name": "TranscribePro",
        "version": "2.1.0",
        "description": "Audio transcription with speaker diarization",
        "protocol": "a2a",
        "endpoint": "https://transcribe-pro.example.com/a2a",
        "capabilities": [
            {
                "skill": "transcribe",
                "inputs": ["audio/wav", "audio/mp3"],
                "output": "text/plain",
                "languages": ["en", "zh", "es"],
                "pricing": {
                    "model": "per_minute",
                    "amount": 0.03,
                    "currency": "USD",
                },
            }
        ],
    }
}

SAMPLE_AGENT_2 = {
    "agent": {
        "name": "SummarizeBot",
        "version": "1.0.0",
        "description": "Text summarization agent",
        "protocol": "a2a",
        "endpoint": "https://summarize-bot.example.com/a2a",
        "capabilities": [
            {
                "skill": "summarize",
                "inputs": ["text/plain"],
                "output": "text/plain",
                "languages": ["en"],
            }
        ],
    }
}


class TestRegistration:
    def test_register_agent(self, client):
        resp = client.post("/api/v1/agents", json=SAMPLE_AGENT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "registered"
        assert "dna:transcribepro:" in data["agent_id"]

    def test_register_multiple_versions(self, client):
        v1 = {"agent": {**SAMPLE_AGENT["agent"], "version": "1.0.0"}}
        v2 = {"agent": {**SAMPLE_AGENT["agent"], "version": "2.0.0"}}

        r1 = client.post("/api/v1/agents", json=v1)
        r2 = client.post("/api/v1/agents", json=v2)

        assert r1.json()["agent_id"] != r2.json()["agent_id"]

    def test_register_persists(self, client):
        """Agent should survive across requests (SQLite persistence)."""
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        agent_id = f"dna:transcribepro:v{SAMPLE_AGENT['agent']['version']}"

        resp = client.get(f"/api/v1/agents/{agent_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "TranscribePro"


class TestListAgents:
    def test_list_empty(self, client):
        resp = client.get("/api/v1/agents")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["agents"] == []

    def test_list_with_agents(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        client.post("/api/v1/agents", json=SAMPLE_AGENT_2)

        resp = client.get("/api/v1/agents")
        assert resp.json()["total"] == 2
        assert len(resp.json()["agents"]) == 2

    def test_list_pagination(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        client.post("/api/v1/agents", json=SAMPLE_AGENT_2)

        resp = client.get("/api/v1/agents?limit=1&offset=0")
        assert len(resp.json()["agents"]) == 1
        assert resp.json()["total"] == 2


class TestGetAgent:
    def test_get_existing(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        agent_id = f"dna:transcribepro:v{SAMPLE_AGENT['agent']['version']}"

        resp = client.get(f"/api/v1/agents/{agent_id}")
        assert resp.status_code == 200
        assert resp.json()["description"] == "Audio transcription with speaker diarization"

    def test_get_nonexistent(self, client):
        resp = client.get("/api/v1/agents/dna:nonexistent:v1.0.0")
        assert resp.status_code == 404


class TestSearch:
    def test_search_by_skill(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        client.post("/api/v1/agents", json=SAMPLE_AGENT_2)

        resp = client.get("/api/v1/agents/search?skill=transcribe")
        assert resp.json()["total"] == 1
        assert resp.json()["agents"][0]["name"] == "TranscribePro"

    def test_search_by_language(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        client.post("/api/v1/agents", json=SAMPLE_AGENT_2)

        resp = client.get("/api/v1/agents/search?language=zh")
        assert resp.json()["total"] == 1

    def test_search_by_max_price(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        client.post("/api/v1/agents", json=SAMPLE_AGENT_2)

        # SummarizeBot has no pricing (= free), so it passes any price filter
        resp = client.get("/api/v1/agents/search?max_price=0.01")
        assert resp.json()["total"] == 1  # Only SummarizeBot (no pricing = free)
        assert resp.json()["agents"][0]["name"] == "SummarizeBot"

        resp = client.get("/api/v1/agents/search?max_price=0.05")
        assert resp.json()["total"] == 2  # Both: TranscribePro (0.03) + SummarizeBot (free)

    def test_search_by_protocol(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)

        resp = client.get("/api/v1/agents/search?protocol=a2a")
        assert resp.json()["total"] == 1

        resp = client.get("/api/v1/agents/search?protocol=mcp")
        assert resp.json()["total"] == 0

    def test_search_no_results(self, client):
        resp = client.get("/api/v1/agents/search?skill=nonexistent")
        assert resp.json()["total"] == 0

    def test_search_pagination(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        client.post("/api/v1/agents", json=SAMPLE_AGENT_2)

        resp = client.get("/api/v1/agents/search?limit=1&offset=0")
        assert len(resp.json()["agents"]) == 1


class TestReviews:
    def test_submit_review(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        agent_id = f"dna:transcribepro:v{SAMPLE_AGENT['agent']['version']}"

        resp = client.post(f"/api/v1/agents/{agent_id}/reviews", json={
            "rating": 5,
            "comment": "Excellent transcription quality",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "review submitted"

    def test_review_nonexistent_agent(self, client):
        resp = client.post("/api/v1/agents/dna:fake:v1.0.0/reviews", json={
            "rating": 3,
            "comment": "Meh",
        })
        assert resp.status_code == 404

    def test_review_invalid_rating(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        agent_id = f"dna:transcribepro:v{SAMPLE_AGENT['agent']['version']}"

        resp = client.post(f"/api/v1/agents/{agent_id}/reviews", json={
            "rating": 6,
            "comment": "Too good",
        })
        assert resp.status_code == 422  # Validation error

    def test_reviews_affect_trust_score(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        agent_id = f"dna:transcribepro:v{SAMPLE_AGENT['agent']['version']}"

        # No reviews — neutral score
        resp1 = client.get(f"/api/v1/agents/{agent_id}/trust")
        score_before = resp1.json()["response_quality"]

        # Add good reviews
        for _ in range(5):
            client.post(f"/api/v1/agents/{agent_id}/reviews", json={
                "rating": 5,
                "comment": "Great!",
            })

        resp2 = client.get(f"/api/v1/agents/{agent_id}/trust")
        score_after = resp2.json()["response_quality"]

        assert score_after >= score_before


class TestTrustScore:
    def test_trust_score_new_agent(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        agent_id = f"dna:transcribepro:v{SAMPLE_AGENT['agent']['version']}"

        resp = client.get(f"/api/v1/agents/{agent_id}/trust")
        assert resp.status_code == 200
        data = resp.json()
        assert 0 <= data["total"] <= 100
        assert data["confidence"] == "low"

    def test_trust_score_nonexistent(self, client):
        resp = client.get("/api/v1/agents/dna:fake:v1.0.0/trust")
        assert resp.status_code == 404


class TestTasks:
    def test_create_task(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        agent_id = f"dna:transcribepro:v{SAMPLE_AGENT['agent']['version']}"

        resp = client.post(f"/api/v1/agents/{agent_id}/tasks", json={
            "description": "Transcribe this meeting recording",
            "max_price": 0.10,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert "task_id" in data

    def test_get_task(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        agent_id = f"dna:transcribepro:v{SAMPLE_AGENT['agent']['version']}"

        create_resp = client.post(f"/api/v1/agents/{agent_id}/tasks", json={
            "description": "Transcribe audio",
        })
        task_id = create_resp.json()["task_id"]

        resp = client.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["description"] == "Transcribe audio"

    def test_get_nonexistent_task(self, client):
        resp = client.get("/api/v1/tasks/fake-task-id")
        assert resp.status_code == 404

    def test_task_persists(self, client):
        """Tasks should survive across requests."""
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        agent_id = f"dna:transcribepro:v{SAMPLE_AGENT['agent']['version']}"

        create_resp = client.post(f"/api/v1/agents/{agent_id}/tasks", json={
            "description": "Persist test",
        })
        task_id = create_resp.json()["task_id"]

        resp = client.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["description"] == "Persist test"


class TestHeartbeat:
    def test_heartbeat(self, client):
        client.post("/api/v1/agents", json=SAMPLE_AGENT)
        agent_id = f"dna:transcribepro:v{SAMPLE_AGENT['agent']['version']}"

        resp = client.post(f"/api/v1/agents/{agent_id}/heartbeat")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_heartbeat_nonexistent(self, client):
        resp = client.post("/api/v1/agents/dna:fake:v1.0.0/heartbeat")
        assert resp.status_code == 404


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "agents_registered" in data

    def test_health_reflects_registrations(self, client):
        resp1 = client.get("/health")
        count_before = resp1.json()["agents_registered"]

        client.post("/api/v1/agents", json=SAMPLE_AGENT)

        resp2 = client.get("/health")
        count_after = resp2.json()["agents_registered"]

        assert count_after == count_before + 1
