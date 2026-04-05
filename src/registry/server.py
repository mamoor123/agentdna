"""
AgentDNA Registry Server — Core API

The central registry where agents register, get discovered, and build trust.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(
    title="AgentDNA Registry",
    description="🧬 DNS for AI Agents — Discovery, Trust & Marketplace",
    version="0.1.0",
)

# In-memory store (swap for PostgreSQL in production)
AGENTS: dict[str, dict] = {}
REVIEWS: dict[str, list] = {}
TASKS: dict[str, dict] = {}


# --- Models ---

class AgentCard(BaseModel):
    agent: dict

class TaskRequest(BaseModel):
    description: str
    input: Optional[dict] = None
    max_price: Optional[float] = None
    currency: str = "USD"
    timeout: str = "5m"
    escrow: bool = True

class ReviewRequest(BaseModel):
    rating: int
    comment: str
    task_id: Optional[str] = None


# --- Registry ---

@app.post("/api/v1/agents")
async def register_agent(card: AgentCard):
    """Register an agent in the registry."""
    agent = card.agent
    name = agent.get("name", "").lower().replace(" ", "-")
    version = agent.get("version", "1.0.0")
    agent_id = f"dna:{name}:v{version.split('.')[0]}"

    AGENTS[agent_id] = {
        "id": agent_id,
        **agent,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "online": True,
        "total_tasks_completed": 0,
    }

    return {"agent_id": agent_id, "status": "registered"}


@app.get("/api/v1/agents")
async def list_agents(limit: int = 20, offset: int = 0):
    """List all registered agents."""
    agents = list(AGENTS.values())[offset:offset + limit]
    return {"agents": agents, "total": len(AGENTS)}


@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details."""
    if agent_id not in AGENTS:
        raise HTTPException(404, f"Agent not found: {agent_id}")
    return AGENTS[agent_id]


@app.get("/api/v1/agents/search")
async def search_agents(
    skill: str = None,
    language: str = None,
    max_price: float = None,
    min_reputation: float = None,
    verified: bool = None,
    protocol: str = None,
    limit: int = 10,
    offset: int = 0,
):
    """Search for agents by capability."""
    results = []

    for agent_id, agent in AGENTS.items():
        # Filter by skill
        if skill:
            caps = agent.get("capabilities", [])
            if not any(skill.lower() in c.get("skill", "").lower() for c in caps):
                continue

        # Filter by language
        if language:
            caps = agent.get("capabilities", [])
            if not any(language in c.get("languages", []) for c in caps):
                continue

        # Filter by protocol
        if protocol and agent.get("protocol") != protocol:
            continue

        results.append(agent)

    return {
        "agents": results[offset:offset + limit],
        "total": len(results),
        "query": {"skill": skill, "language": language, "protocol": protocol},
    }


# --- Trust ---

@app.get("/api/v1/agents/{agent_id}/trust")
async def get_trust_score(agent_id: str):
    """Get trust score for an agent."""
    if agent_id not in AGENTS:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    agent_reviews = REVIEWS.get(agent_id, [])
    avg_rating = (
        sum(r["rating"] for r in agent_reviews) / len(agent_reviews)
        if agent_reviews
        else 0
    )

    # Simplified scoring (production version uses the full algorithm)
    return {
        "agent_id": agent_id,
        "total": min(100, int(avg_rating * 20)),
        "task_completion": min(40, AGENTS[agent_id].get("total_tasks_completed", 0) // 100),
        "response_quality": int(avg_rating * 5),
        "latency_reliability": 12,
        "uptime_score": 8,
        "verification_bonus": 10 if AGENTS[agent_id].get("verified") else 0,
        "review_count": len(agent_reviews),
    }


@app.post("/api/v1/agents/{agent_id}/reviews")
async def submit_review(agent_id: str, review: ReviewRequest):
    """Submit a review for an agent."""
    if agent_id not in AGENTS:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    if agent_id not in REVIEWS:
        REVIEWS[agent_id] = []

    REVIEWS[agent_id].append({
        "rating": review.rating,
        "comment": review.comment,
        "task_id": review.task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"status": "review submitted"}


# --- Marketplace ---

@app.post("/api/v1/agents/{agent_id}/tasks")
async def create_task(agent_id: str, task: TaskRequest):
    """Create a task for an agent (hire them)."""
    if agent_id not in AGENTS:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "task_id": task_id,
        "agent_id": agent_id,
        "description": task.description,
        "input": task.input,
        "max_price": task.max_price,
        "currency": task.currency,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return {"task_id": task_id, "status": "pending"}


@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task status."""
    if task_id not in TASKS:
        raise HTTPException(404, f"Task not found: {task_id}")
    return TASKS[task_id]


# --- Heartbeat ---

@app.post("/api/v1/agents/{agent_id}/heartbeat")
async def heartbeat(agent_id: str):
    """Agent heartbeat."""
    if agent_id not in AGENTS:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    AGENTS[agent_id]["online"] = True
    AGENTS[agent_id]["last_heartbeat"] = datetime.now(timezone.utc).isoformat()

    return {"status": "ok"}


# --- Health ---

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agents_registered": len(AGENTS),
        "tasks_created": len(TASKS),
        "version": "0.1.0",
    }
