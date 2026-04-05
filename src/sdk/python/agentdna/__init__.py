"""
🧬 AgentDNA — DNS for AI Agents

Discovery, Trust & Marketplace for AI agents.
The missing layer between A2A and your agents.

Usage:
    from agentdna import find_agent, hire_agent, register_agent

    # Find an agent
    agent = find_agent(skill="transcribe", language="zh", max_price=0.03)

    # Hire an agent
    result = await hire_agent(agent=agent.id, task="Transcribe this", input_file="audio.wav")

    # Register your agent
    register_agent("./agentdna.yaml")
"""

from agentdna.models import Agent, AgentSearchResult, Capability, Pricing, TrustScore, TaskResult
from agentdna.registry import register_agent, load_agent_card, generate_agent_card
from agentdna.discovery import find_agent, search_agents
from agentdna.marketplace import hire_agent, hire_agent_sync

__version__ = "0.1.0"
__all__ = [
    # Client (lazy import to avoid httpx requirement at import time)
    "AgentDNAClient",
    # Models
    "Agent",
    "AgentSearchResult",
    "Capability",
    "Pricing",
    "TrustScore",
    "TaskResult",
    # Registry
    "register_agent",
    "load_agent_card",
    "generate_agent_card",
    # Discovery
    "find_agent",
    "search_agents",
    # Marketplace
    "hire_agent",
    "hire_agent_sync",
]


def __getattr__(name: str):
    """Lazy import for AgentDNAClient to avoid requiring httpx at import time."""
    if name == "AgentDNAClient":
        from agentdna.client import AgentDNAClient
        return AgentDNAClient
    raise AttributeError(f"module 'agentdna' has no attribute {name!r}")
