"""
AgentDNA Registry Server — Core API

The central registry where agents register, get discovered, and build trust.
Uses SQLite for persistence (survives restarts).

Auth:
- GET requests: open (search, list, view)
- POST/PUT/DELETE: require API key (Authorization: Bearer <key>)
- Rate limiting: 60 req/min default, 10 req/min for verification
- Set AGENTDNA_AUTH_DISABLED=1 to disable auth (dev mode)
- Set AGENTNA_API_KEYS=key1,key2 to enable auth
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from agentdna.trust.scorer import (
    LatencyStats,
    QualityStats,
    TaskStats,
    TrustScorer,
    UptimeStats,
)
from agentdna.sandbox.verifier import AgentVerifier

from registry.storage import (
    save_agent,
    get_agent,
    list_agents,
    get_all_agents,
    update_heartbeat,
    set_verified,
    save_review,
    get_reviews,
    save_task,
    get_task as get_task_from_db,
    save_verification_report,
    get_verification_report,
    get_registry_stats,
)
from registry.auth import AuthMiddleware, get_auth_status

app = FastAPI(
    title="AgentDNA Registry",
    description="🧬 DNS for AI Agents — Discovery, Trust & Marketplace",
    version="0.3.0",
)

# Add auth + rate limiting middleware
app.add_middleware(AuthMiddleware)

_trust_scorer = TrustScorer()


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
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    comment: str
    task_id: Optional[str] = None


# --- Registry ---

@app.post("/api/v1/agents")
async def register_agent(card: AgentCard):
    """Register an agent in the registry."""
    agent = card.agent
    name = agent.get("name", "").lower().replace(" ", "-")
    version = agent.get("version", "1.0.0")
    safe_version = version.replace(":", "-")
    agent_id = f"dna:{name}:v{safe_version}"

    agent_data = {
        "id": agent_id,
        **agent,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "online": True,
        "total_submitted": 0,
        "total_tasks_completed": 0,
        "total_failed": 0,
        "total_timed_out": 0,
        "tasks_within_sla": 0,
        "total_tasks_with_timing": 0,
        "promised_latency_seconds": 0,
        "uptime_checks": 0,
        "uptime_successes": 0,
        "verified": False,
    }

    save_agent(agent_id, agent_data)
    return {"agent_id": agent_id, "status": "registered"}


@app.get("/api/v1/agents")
async def list_agents_endpoint(limit: int = 20, offset: int = 0):
    """List all registered agents."""
    agents, total = list_agents(limit=limit, offset=offset)
    return {"agents": agents, "total": total}


@app.get("/api/v1/agents/search")
async def search_agents(
    skill: str = None,
    language: str = None,
    max_price: float = None,
    min_reputation: float = None,
    verified: bool = None,
    protocol: str = None,
    tags: str = None,
    limit: int = 10,
    offset: int = 0,
):
    """Search for agents by capability."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    all_agents = get_all_agents()
    results = []

    for agent_id, agent in all_agents.items():
        # Filter by skill
        if skill:
            caps = [c for c in agent.get("capabilities", []) if c]
            if not any(skill.lower() in (c.get("skill") or "").lower() for c in caps):
                continue

        # Filter by language
        if language:
            caps = [c for c in agent.get("capabilities", []) if c]
            if not any(language in (c.get("languages") or []) for c in caps):
                continue

        # Filter by protocol
        if protocol and agent.get("protocol") != protocol:
            continue

        # Filter by tags — agent must have ALL requested tags
        if tag_list:
            agent_tags = agent.get("metadata", {}).get("tags", [])
            if not all(t in agent_tags for t in tag_list):
                continue

        # Filter by max_price
        if max_price is not None:
            caps = [c for c in agent.get("capabilities", []) if c]
            prices = [
                c.get("pricing", {}).get("amount", 0)
                for c in caps
                if c.get("pricing")
            ]
            if prices and min(prices) > max_price:
                continue

        # Filter by verified status
        if verified is not None and agent.get("verified", False) != verified:
            continue

        # Filter by min_reputation
        if min_reputation is not None:
            agent_reviews = get_reviews(agent_id)
            avg_rating = (
                sum(r["rating"] for r in agent_reviews) / len(agent_reviews)
                if agent_reviews else 0
            )
            tasks = TaskStats(
                total_submitted=agent.get("total_submitted", 0),
                total_completed=agent.get("total_tasks_completed", 0),
                total_failed=agent.get("total_failed", 0),
                total_timed_out=agent.get("total_timed_out", 0),
            )
            quality = QualityStats(avg_rating=avg_rating, review_count=len(agent_reviews))
            latency = LatencyStats(
                tasks_within_sla=agent.get("tasks_within_sla", 0),
                total_tasks_with_timing=agent.get("total_tasks_with_timing", 0),
                promised_latency_seconds=agent.get("promised_latency_seconds", 0),
            )
            uptime = UptimeStats(
                total_checks=agent.get("uptime_checks", 0),
                successful_checks=agent.get("uptime_successes", 0),
            )
            score = _trust_scorer.compute(
                tasks=tasks, quality=quality, latency=latency,
                uptime=uptime, verified=agent.get("verified", False),
            )
            if score.total < min_reputation:
                continue

        results.append(agent)

    return {
        "agents": results[offset:offset + limit],
        "total": len(results),
        "query": {
            "skill": skill,
            "language": language,
            "protocol": protocol,
            "max_price": max_price,
            "min_reputation": min_reputation,
            "verified": verified,
        },
    }


@app.get("/api/v1/agents/{agent_id}")
async def get_agent_endpoint(agent_id: str):
    """Get agent details."""
    agent = get_agent(agent_id)
    if agent is None:
        raise HTTPException(404, f"Agent not found: {agent_id}")
    return agent


# --- Trust ---

@app.get("/api/v1/agents/{agent_id}/trust")
async def get_trust_score_endpoint(agent_id: str):
    """Get trust score for an agent using the full scoring algorithm."""
    agent = get_agent(agent_id)
    if agent is None:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    agent_reviews = get_reviews(agent_id)
    avg_rating = (
        sum(r["rating"] for r in agent_reviews) / len(agent_reviews)
        if agent_reviews else 0
    )

    tasks = TaskStats(
        total_submitted=agent.get("total_submitted", 0),
        total_completed=agent.get("total_tasks_completed", 0),
        total_failed=agent.get("total_failed", 0),
        total_timed_out=agent.get("total_timed_out", 0),
    )

    quality = QualityStats(
        avg_rating=avg_rating,
        review_count=len(agent_reviews),
    )

    latency = LatencyStats(
        tasks_within_sla=agent.get("tasks_within_sla", 0),
        total_tasks_with_timing=agent.get("total_tasks_with_timing", 0),
        promised_latency_seconds=agent.get("promised_latency_seconds", 0),
    )

    uptime = UptimeStats(
        total_checks=agent.get("uptime_checks", 0),
        successful_checks=agent.get("uptime_successes", 0),
    )

    score = _trust_scorer.compute(
        tasks=tasks,
        quality=quality,
        latency=latency,
        uptime=uptime,
        verified=agent.get("verified", False),
    )

    return {
        "agent_id": agent_id,
        **score.to_dict(),
        "review_count": len(agent_reviews),
    }


@app.post("/api/v1/agents/{agent_id}/reviews")
async def submit_review(agent_id: str, review: ReviewRequest):
    """Submit a review for an agent."""
    agent = get_agent(agent_id)
    if agent is None:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    save_review(agent_id, {
        "rating": review.rating,
        "comment": review.comment,
        "task_id": review.task_id,
    })

    return {"status": "review submitted"}


# --- Marketplace ---

@app.post("/api/v1/agents/{agent_id}/tasks")
async def create_task(agent_id: str, task: TaskRequest):
    """Create a task for an agent (hire them)."""
    agent = get_agent(agent_id)
    if agent is None:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    task_id = str(uuid.uuid4())
    task_data = {
        "task_id": task_id,
        "agent_id": agent_id,
        "description": task.description,
        "input": task.input,
        "max_price": task.max_price,
        "currency": task.currency,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    save_task(task_id, agent_id, task_data)
    return {"task_id": task_id, "status": "pending"}


@app.get("/api/v1/tasks/{task_id}")
async def get_task_endpoint(task_id: str):
    """Get task status."""
    task = get_task_from_db(task_id)
    if task is None:
        raise HTTPException(404, f"Task not found: {task_id}")
    return task


# --- Heartbeat ---

@app.post("/api/v1/agents/{agent_id}/heartbeat")
async def heartbeat(agent_id: str):
    """Agent heartbeat."""
    if not update_heartbeat(agent_id):
        raise HTTPException(404, f"Agent not found: {agent_id}")
    return {"status": "ok"}


# --- Health ---

@app.get("/health")
async def health():
    stats = get_registry_stats()
    auth = get_auth_status()
    return {
        "status": "healthy",
        "version": "0.3.0",
        **stats,
        "auth": auth,
    }


# --- Sandbox Verification ---

@app.post("/api/v1/agents/{agent_id}/verify")
async def verify_agent_endpoint(agent_id: str):
    """Run remote probe verification against an agent."""
    agent = get_agent(agent_id)
    if agent is None:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    endpoint = agent.get("endpoint", "")
    protocol = agent.get("protocol", "a2a")

    if not endpoint:
        raise HTTPException(400, "Agent has no endpoint configured")

    verifier = AgentVerifier()
    report = await verifier.verify(
        agent_id=agent_id,
        endpoint=endpoint,
        protocol=protocol,
        agent_card=agent,
    )

    report_dict = report.to_dict()
    save_verification_report(agent_id, report_dict)

    # Update agent verification status
    if report.passed:
        set_verified(agent_id, True)

    return report_dict


@app.get("/api/v1/agents/{agent_id}/verify")
async def get_verification_report_endpoint(agent_id: str):
    """Get the latest verification report for an agent."""
    report = get_verification_report(agent_id)
    if report is None:
        raise HTTPException(404, f"No verification report found for: {agent_id}")
    return report
