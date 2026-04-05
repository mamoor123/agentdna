"""AgentDNA data models."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Pricing:
    """Pricing information for an agent capability."""

    model: str  # "free" | "per_call" | "per_minute" | "per_token" | "per_item"
    amount: float = 0.0
    currency: str = "USD"
    free_tier: int = 0

    def display(self) -> str:
        if self.model == "free":
            return "Free"
        symbols = {"USD": "$", "EUR": "€", "GBP": "£", "CNY": "¥"}
        sym = symbols.get(self.currency, self.currency + " ")
        labels = {
            "per_call": "/call",
            "per_minute": "/min",
            "per_token": "/1K tokens",
            "per_item": "/item",
        }
        return f"{sym}{self.amount:.2f}{labels.get(self.model, '')}"


@dataclass
class Capability:
    """A single skill/capability of an agent."""

    skill: str
    description: str = ""
    inputs: list[str] = field(default_factory=list)
    output: str = ""
    languages: list[str] = field(default_factory=list)
    pricing: Optional[Pricing] = None


@dataclass
class SLA:
    """Service Level Agreement."""

    avg_latency: str = ""
    uptime: str = ""


@dataclass
class TrustScore:
    """Trust/reputation score for an agent."""

    total: int = 0
    task_completion: int = 0
    response_quality: int = 0
    latency_reliability: int = 0
    uptime_score: int = 0
    verification_bonus: int = 0

    @property
    def tier(self) -> str:
        if self.total >= 90:
            return "Exceptional 🏆"
        elif self.total >= 75:
            return "Excellent ⭐"
        elif self.total >= 60:
            return "Good ✅"
        elif self.total >= 40:
            return "Fair ⚠️"
        return "Unverified ❓"


@dataclass
class Agent:
    """An agent in the AgentDNA registry."""

    id: str
    name: str
    version: str
    description: str
    protocol: str
    endpoint: str
    capabilities: list[Capability] = field(default_factory=list)
    trust_score: Optional[TrustScore] = None
    tags: list[str] = field(default_factory=list)
    verified: bool = False
    owner_name: str = ""
    repository: str = ""

    def __repr__(self):
        score = f" (DNA: {self.trust_score.total}/100)" if self.trust_score else ""
        verified = " 🏆" if self.verified else ""
        return f"<Agent {self.name} v{self.version}{score}{verified}>"


@dataclass
class AgentSearchResult:
    """Search result containing multiple agents."""

    agents: list[Agent] = field(default_factory=list)
    total: int = 0
    query: dict = field(default_factory=dict)

    def best(self) -> Optional[Agent]:
        """Return the highest-scored agent."""
        if not self.agents:
            return None
        return max(
            self.agents,
            key=lambda a: a.trust_score.total if a.trust_score else 0,
        )


@dataclass
class TaskResult:
    """Result of hiring an agent for a task."""

    task_id: str
    agent_id: str
    status: str  # "pending" | "in_progress" | "completed" | "failed" | "refunded"
    output: Optional[str] = None
    cost: float = 0.0
    currency: str = "USD"
    duration_seconds: float = 0.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == "completed"
