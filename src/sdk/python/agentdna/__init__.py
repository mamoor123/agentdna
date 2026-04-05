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

from agentdna.client import AgentDNAClient
from agentdna.models import Agent, AgentSearchResult, TrustScore, TaskResult
from agentdna.registry import register_agent, load_agent_card
from agentdna.discovery import find_agent, search_agents
from agentdna.marketplace import hire_agent

__version__ = "0.1.0"
__all__ = [
    "AgentDNAClient",
    "Agent",
    "AgentSearchResult",
    "TrustScore",
    "TaskResult",
    "register_agent",
    "load_agent_card",
    "find_agent",
    "search_agents",
    "hire_agent",
]
