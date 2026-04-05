"""AgentDNA API client."""

import os
from typing import Optional

import httpx

AGENTDNA_API_URL = os.environ.get("AGENTDNA_API_URL", "https://api.agentdna.dev")
AGENTDNA_API_KEY = os.environ.get("AGENTDNA_API_KEY", "")


class AgentDNAClient:
    """Client for the AgentDNA registry API."""

    def __init__(
        self,
        api_url: str = AGENTDNA_API_URL,
        api_key: str = AGENTDNA_API_KEY,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json",
                "User-Agent": f"agentdna-python/{__import__('agentdna').__version__}",
            },
            timeout=30.0,
        )

    def _get(self, path: str, params: dict = None) -> dict:
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict = None) -> dict:
        resp = self._client.post(path, json=data)
        resp.raise_for_status()
        return resp.json()

    # --- Registry ---

    def register(self, agent_card: dict) -> dict:
        """Register an agent in the registry."""
        return self._post("/api/v1/agents", data=agent_card)

    def get_agent(self, agent_id: str) -> dict:
        """Get agent details by DNA ID."""
        return self._get(f"/api/v1/agents/{agent_id}")

    def list_agents(self, limit: int = 20, offset: int = 0) -> dict:
        """List registered agents."""
        return self._get("/api/v1/agents", params={"limit": limit, "offset": offset})

    # --- Discovery ---

    def search(
        self,
        skill: str = None,
        language: str = None,
        max_price: float = None,
        min_reputation: float = None,
        verified: bool = None,
        protocol: str = None,
        tags: list[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict:
        """Search for agents by capability."""
        params = {"limit": limit, "offset": offset}
        if skill:
            params["skill"] = skill
        if language:
            params["language"] = language
        if max_price is not None:
            params["max_price"] = max_price
        if min_reputation is not None:
            params["min_reputation"] = min_reputation
        if verified is not None:
            params["verified"] = str(verified).lower()
        if protocol:
            params["protocol"] = protocol
        if tags:
            params["tags"] = ",".join(tags)
        return self._get("/api/v1/agents/search", params=params)

    # --- Trust ---

    def get_trust_score(self, agent_id: str) -> dict:
        """Get the trust/reputation score for an agent."""
        return self._get(f"/api/v1/agents/{agent_id}/trust")

    def submit_review(self, agent_id: str, rating: int, comment: str, task_id: str = None) -> dict:
        """Submit a review for an agent."""
        return self._post(
            f"/api/v1/agents/{agent_id}/reviews",
            data={"rating": rating, "comment": comment, "task_id": task_id},
        )

    # --- Marketplace ---

    def create_task(self, agent_id: str, task: dict) -> dict:
        """Create a task for an agent (hire them)."""
        return self._post(f"/api/v1/agents/{agent_id}/tasks", data=task)

    def get_task(self, task_id: str) -> dict:
        """Get task status and result."""
        return self._get(f"/api/v1/tasks/{task_id}")

    # --- Heartbeat ---

    def ping(self, agent_id: str) -> dict:
        """Send a heartbeat ping for an agent."""
        return self._post(f"/api/v1/agents/{agent_id}/heartbeat")

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
