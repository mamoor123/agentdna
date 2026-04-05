"""
AgentDNA Plugin for CrewAI

Extends CrewAI crews to:
1. Auto-register with the AgentDNA registry
2. Discover and delegate to external agents
3. Track task completion and quality metrics

Usage:
    from crewai import Agent, Task, Crew
    from agentdna.plugins.crewai import AgentDNACrew

    researcher = Agent(role="Researcher", goal="Find information", backstory="...")
    writer = Agent(role="Writer", goal="Write reports", backstory="...")

    crew = AgentDNACrew(
        agents=[researcher, writer],
        tasks=[...],
        agent_card={
            "name": "ResearchCrew",
            "version": "1.0.0",
            "description": "Research and writing crew",
            "protocol": "a2a",
            "endpoint": "https://my-crew.example.com/a2a",
            "capabilities": [
                {"skill": "research", "inputs": ["text/plain"], "output": "text/plain"},
                {"skill": "write", "inputs": ["text/plain"], "output": "text/plain"},
            ],
        },
    )

    result = crew.kickoff(inputs={"topic": "AI agents"})
"""

from __future__ import annotations

from typing import Any, Optional

from agentdna.client import AgentDNAClient
from agentdna.discovery import find_agent


class AgentDNACrew:
    """
    CrewAI Crew with AgentDNA integration.

    Wraps a CrewAI crew to add:
    - Registry auto-registration
    - External agent discovery
    - Performance tracking
    """

    def __init__(
        self,
        agents: list = None,
        tasks: list = None,
        agent_card: dict = None,
        api_key: str = None,
        auto_register: bool = True,
        **crew_kwargs,
    ):
        self.agents = agents or []
        self.tasks = tasks or []
        self.agent_card = agent_card
        self.api_key = api_key
        self._client = AgentDNAClient(api_key=api_key or "")
        self._registered = False
        self._stats = {
            "total_kickoffs": 0,
            "total_tasks_completed": 0,
            "total_errors": 0,
        }

        # Lazy import CrewAI
        try:
            from crewai import Crew
            self._inner_crew = Crew(
                agents=agents or [],
                tasks=tasks or [],
                **crew_kwargs,
            )
        except ImportError:
            self._inner_crew = None

        if auto_register and agent_card:
            self._register()

    def _register(self):
        """Register this crew in the AgentDNA registry."""
        try:
            if self.agent_card:
                self._client.register(self.agent_card)
                self._registered = True
        except Exception:
            pass

    def kickoff(self, inputs: dict = None) -> Any:
        """Run the crew with AgentDNA tracking."""
        self._stats["total_kickoffs"] += 1

        try:
            if self._inner_crew:
                result = self._inner_crew.kickoff(inputs=inputs or {})
            else:
                result = {"status": "completed", "note": "CrewAI not installed — mock result"}

            self._stats["total_tasks_completed"] += len(self.tasks)
            return result
        except Exception:
            self._stats["total_errors"] += 1
            raise

    async def kickoff_async(self, inputs: dict = None) -> Any:
        """Async kickoff if supported."""
        self._stats["total_kickoffs"] += 1

        try:
            if self._inner_crew and hasattr(self._inner_crew, "kickoff_async"):
                result = await self._inner_crew.kickoff_async(inputs=inputs or {})
            else:
                result = self.kickoff(inputs=inputs)

            self._stats["total_tasks_completed"] += len(self.tasks)
            return result
        except Exception:
            self._stats["total_errors"] += 1
            raise

    # --- Agent Discovery ---

    @staticmethod
    def find_agent_for_task(
        skill: str,
        language: str = None,
        max_price: float = None,
        api_key: str = None,
    ) -> Optional[dict]:
        """
        Find an external agent from the AgentDNA registry.

        Use this in your CrewAI tasks to delegate work to specialized agents.

        Example:
            # Inside a task callback:
            def delegate_transcription(audio_path):
                agent = AgentDNACrew.find_agent_for_task("transcribe", language="en")
                if agent:
                    # Send to that agent via A2A
                    return call_external_agent(agent["endpoint"], audio_path)
                return "No agent found"
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

    def get_stats(self) -> dict:
        """Get crew performance statistics."""
        return dict(self._stats)

    def __repr__(self):
        status = "registered" if self._registered else "local"
        n_agents = len(self.agents)
        n_tasks = len(self.tasks)
        return f"<AgentDNACrew {status} agents={n_agents} tasks={n_tasks}>"

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
