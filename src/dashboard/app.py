"""
AgentDNA Web Dashboard

Beautiful agent profile pages + search UI.
Serves as the public-facing interface for the AgentDNA registry.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

app = FastAPI(title="AgentDNA Dashboard", version="0.1.0")

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# --- Mock data for static demo (replace with real API calls) ---

DEMO_AGENTS = {
    "dna:transcribe-pro:v2": {
        "id": "dna:transcribe-pro:v2",
        "name": "TranscribePro",
        "version": "2.1.0",
        "description": "High-accuracy audio transcription with speaker diarization. Supports 7 languages with 99.2% accuracy.",
        "protocol": "a2a",
        "endpoint": "https://transcribe-pro.example.com/a2a",
        "verified": True,
        "total_tasks_completed": 47832,
        "owner": {"name": "Acme AI Labs", "url": "https://acme-ai.example.com"},
        "capabilities": [
            {
                "skill": "transcribe",
                "description": "Transcribe audio files to text with timestamps",
                "inputs": ["audio/wav", "audio/mp3", "audio/m4a"],
                "output": "text/plain",
                "languages": ["en", "zh", "es", "fr", "de", "ja", "ko"],
                "pricing": {"model": "per_minute", "amount": 0.02, "currency": "USD"},
            },
            {
                "skill": "diarize",
                "description": "Identify and separate speakers",
                "inputs": ["audio/wav", "audio/mp3"],
                "output": "application/json",
                "languages": ["en", "zh"],
                "pricing": {"model": "per_minute", "amount": 0.05, "currency": "USD"},
            },
        ],
        "trust_score": {
            "total": 92,
            "task_completion": 38,
            "response_quality": 23,
            "latency_reliability": 14,
            "uptime_score": 9,
            "verification_bonus": 8,
            "tier": "Exceptional",
            "badge": "🏆",
            "confidence": "high",
        },
        "metadata": {
            "framework": "custom",
            "hosting": "cloud",
            "region": "us-east-1",
            "tags": ["transcription", "audio", "speech-to-text"],
        },
        "uptime": "99.7%",
        "avg_latency": "12s/min",
        "reviews": [
            {"rating": 5, "comment": "Blazing fast, accurate Chinese transcription", "date": "2026-03-28"},
            {"rating": 5, "comment": "Best transcription agent I've used. Speaker diarization is spot on.", "date": "2026-03-15"},
            {"rating": 4, "comment": "Good but occasional speaker errors with 3+ speakers", "date": "2026-02-20"},
        ],
    },
    "dna:code-reviewer:v1": {
        "id": "dna:code-reviewer:v1",
        "name": "CodeReviewer",
        "version": "1.3.0",
        "description": "Automated code review agent. Checks for bugs, security issues, and style violations across 20+ languages.",
        "protocol": "a2a",
        "endpoint": "https://code-reviewer.example.com/a2a",
        "verified": True,
        "total_tasks_completed": 12450,
        "owner": {"name": "DevTools Inc", "url": "https://devtools.example.com"},
        "capabilities": [
            {
                "skill": "review",
                "description": "Review a code diff or file",
                "inputs": ["text/plain", "text/x-python", "text/x-java"],
                "output": "application/json",
                "languages": ["en"],
                "pricing": {"model": "per_call", "amount": 0.10, "currency": "USD"},
            },
        ],
        "trust_score": {
            "total": 85,
            "task_completion": 36,
            "response_quality": 21,
            "latency_reliability": 13,
            "uptime_score": 9,
            "verification_bonus": 6,
            "tier": "Excellent",
            "badge": "⭐",
            "confidence": "high",
        },
        "metadata": {
            "framework": "langchain",
            "hosting": "cloud",
            "region": "eu-west-1",
            "tags": ["code-review", "security", "linting"],
        },
        "uptime": "99.5%",
        "avg_latency": "8s/review",
        "reviews": [
            {"rating": 5, "comment": "Caught a SQL injection vulnerability I missed", "date": "2026-03-30"},
            {"rating": 4, "comment": "Good general review, but misses domain-specific patterns", "date": "2026-03-10"},
        ],
    },
}


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page — search and browse agents."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "agents": list(DEMO_AGENTS.values()),
            "total": len(DEMO_AGENTS),
        },
    )


@app.get("/agent/{agent_id:path}", response_class=HTMLResponse)
async def agent_profile(request: Request, agent_id: str):
    """Agent profile page."""
    agent = DEMO_AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    return templates.TemplateResponse(
        "agent.html",
        {"request": request, "agent": agent},
    )


@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = "", protocol: str = ""):
    """Search results page."""
    results = []
    for agent in DEMO_AGENTS.values():
        if q.lower() in agent["name"].lower() or q.lower() in agent["description"].lower():
            if not protocol or agent["protocol"] == protocol:
                results.append(agent)

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "query": q,
            "agents": results,
            "total": len(results),
        },
    )
