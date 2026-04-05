"""
AgentDNA Plugin for LangChain / LangGraph

Wraps any LangChain chain or agent to:
1. Auto-register with the AgentDNA registry
2. Discover and call other agents as tools
3. Track trust metrics (task completion, latency)

Usage:
    from langchain.agents import AgentExecutor
    from agentdna.plugins.langchain import AgentDNAWrapper

    # Wrap your existing agent
    executor = AgentExecutor.from_agent_and_tools(agent=my_agent, tools=my_tools)
    wrapped = AgentDNAWrapper(executor, agent_card={
        "name": "MyLangChainAgent",
        "version": "1.0.0",
        "description": "Research agent built with LangChain",
        "protocol": "a2a",
        "endpoint": "https://my-agent.example.com/a2a",
        "capabilities": [
            {"skill": "research", "inputs": ["text/plain"], "output": "text/plain"}
        ],
    })

    # Run as usual — now with AgentDNA integration
    result = wrapped.run("Research quantum computing trends")
"""

from __future__ import annotations

import time
from typing import Any, Optional

from agentdna.client import AgentDNAClient
from agentdna.discovery import find_agent


class AgentDNAWrapper:
    """
    Wraps a LangChain agent/chain with AgentDNA capabilities.

    Features:
    - Auto-registration on first use
    - Trust metric tracking
    - Agent discovery as a LangChain Tool
    """

    def __init__(
        self,
        chain: Any,
        agent_card: dict = None,
        api_key: str = None,
        auto_register: bool = True,
    ):
        self.chain = chain
        self.agent_card = agent_card
        self.api_key = api_key
        self._client = AgentDNAClient(api_key=api_key or "")
        self._registered = False
        self._stats = {
            "total_calls": 0,
            "total_errors": 0,
            "total_latency_ms": 0,
        }

        if auto_register and agent_card:
            self._register()

    def _register(self):
        """Register this agent in the AgentDNA registry."""
        try:
            if self.agent_card:
                self._client.register(self.agent_card)
                self._registered = True
        except Exception:
            pass  # silent fail — don't break the agent

    def run(self, input: str, **kwargs) -> str:
        """Run the wrapped chain with AgentDNA tracking."""
        start = time.time()
        self._stats["total_calls"] += 1

        try:
            result = self.chain.run(input, **kwargs)
            elapsed = (time.time() - start) * 1000
            self._stats["total_latency_ms"] += elapsed
            return result
        except Exception:
            self._stats["total_errors"] += 1
            raise

    async def arun(self, input: str, **kwargs) -> str:
        """Async run with tracking."""
        start = time.time()
        self._stats["total_calls"] += 1

        try:
            if hasattr(self.chain, "arun"):
                result = await self.chain.arun(input, **kwargs)
            else:
                result = self.chain.run(input, **kwargs)
            elapsed = (time.time() - start) * 1000
            self._stats["total_latency_ms"] += elapsed
            return result
        except Exception:
            self._stats["total_errors"] += 1
            raise

    def invoke(self, input: Any, **kwargs) -> Any:
        """LangChain-compatible invoke method."""
        start = time.time()
        self._stats["total_calls"] += 1

        try:
            if hasattr(self.chain, "invoke"):
                result = self.chain.invoke(input, **kwargs)
            else:
                result = self.chain.run(input, **kwargs)
            elapsed = (time.time() - start) * 1000
            self._stats["total_latency_ms"] += elapsed
            return result
        except Exception:
            self._stats["total_errors"] += 1
            raise

    def get_stats(self) -> dict:
        """Get current performance statistics."""
        stats = dict(self._stats)
        if stats["total_calls"] > 0:
            stats["avg_latency_ms"] = stats["total_latency_ms"] / stats["total_calls"]
        return stats

    # --- Agent Discovery ---

    @staticmethod
    def find_agent_for_task(
        skill: str,
        language: str = None,
        max_price: float = None,
        api_key: str = None,
    ) -> Optional[dict]:
        """
        Find another agent from the registry that can handle a task.

        Example:
            transcriber = AgentDNAWrapper.find_agent_for_task(
                skill="transcribe",
                language="zh",
                max_price=0.03,
            )
            if transcriber:
                # Call that agent via A2A
                pass
        """
        agent = find_agent(
            skill=skill,
            language=language,
            max_price=max_price,
            api_key=api_key,
        )
        if agent:
            return {
                "id": agent.id,
                "name": agent.name,
                "endpoint": agent.endpoint,
                "trust_score": agent.trust_score.total if agent.trust_score else 0,
            }
        return None

    def __repr__(self):
        status = "registered" if self._registered else "local"
        return f"<AgentDNAWrapper {status} calls={self._stats['total_calls']}>"

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
