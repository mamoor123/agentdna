"""Tests for Registry Auth — authentication middleware behavior."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Use temp database
_tmpdir = tempfile.mkdtemp()
os.environ["AGENTDNA_REGISTRY_DB_PATH"] = os.path.join(_tmpdir, "test_auth_registry.db")
os.environ["AGENTDNA_DB_PATH"] = os.path.join(_tmpdir, "test_auth_observe.db")

from registry.server import app  # noqa: E402


@pytest.fixture
def client():
    db_path = os.environ["AGENTDNA_REGISTRY_DB_PATH"]
    if os.path.exists(db_path):
        os.remove(db_path)
    from registry import storage
    storage._get_conn()
    return TestClient(app)


SAMPLE_AGENT = {
    "agent": {
        "name": "AuthTestAgent",
        "version": "1.0.0",
        "description": "Test agent",
        "protocol": "a2a",
        "endpoint": "https://test.example.com/a2a",
        "capabilities": [{"skill": "test"}],
    }
}


class TestAuthBehavior:
    """Test auth middleware behavior in dev mode (auth disabled)."""

    def test_register_works(self, client):
        """POST should work when auth is disabled."""
        resp = client.post("/api/v1/agents", json=SAMPLE_AGENT)
        assert resp.status_code == 200

    def test_search_works(self, client):
        """GET should always work."""
        resp = client.get("/api/v1/agents/search?skill=test")
        assert resp.status_code == 200

    def test_health_shows_auth_status(self, client):
        """Health endpoint should show auth configuration."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "auth" in data
        assert "auth_disabled" in data["auth"]
        assert "rate_limit_disabled" in data["auth"]

    def test_public_paths_accessible(self, client):
        """Public paths should always be accessible."""
        for path in ["/health", "/docs", "/openapi.json"]:
            resp = client.get(path)
            assert resp.status_code == 200, f"{path} should be accessible"
