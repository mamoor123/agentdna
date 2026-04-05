"""Agent discovery and search."""

from typing import Optional

from agentdna.client import AgentDNAClient
from agentdna.models import Agent, AgentSearchResult, Capability, Pricing, TrustScore


def _parse_agent(data: dict) -> Agent:
    """Parse API response into Agent model."""
    capabilities = []
    for cap in data.get("capabilities", []) or []:
        if not cap:
            continue
        pricing = None
        if cap.get("pricing"):
            pricing = Pricing(**cap["pricing"])
        capabilities.append(
            Capability(
                skill=cap.get("skill", ""),
                description=cap.get("description", ""),
                inputs=cap.get("inputs", []),
                output=cap.get("output", ""),
                languages=cap.get("languages", []),
                pricing=pricing,
            )
        )

    trust = None
    if data.get("trust_score"):
        trust = TrustScore(**data["trust_score"])
    elif data.get("trust_total") is not None:
        # Server returns trust fields with trust_ prefix (flat structure)
        trust = TrustScore(
            total=data.get("trust_total", 0),
            task_completion=data.get("trust_task_completion", 0),
            response_quality=data.get("trust_response_quality", 0),
            latency_reliability=data.get("trust_latency_reliability", 0),
            uptime_score=data.get("trust_uptime_score", 0),
            verification_bonus=data.get("trust_verification_bonus", 0),
        )
    elif (
        isinstance(data.get("total"), int)
        and "task_completion" in data
    ):
        # Flat trust fields (e.g., direct trust endpoint response)
        trust = TrustScore(
            total=data.get("total", 0),
            task_completion=data.get("task_completion", 0),
            response_quality=data.get("response_quality", 0),
            latency_reliability=data.get("latency_reliability", 0),
            uptime_score=data.get("uptime_score", 0),
            verification_bonus=data.get("verification_bonus", 0),
        )

    # Safe nested access — handles None values at any level
    metadata = data.get("metadata") or {}
    owner = data.get("owner") or {}

    return Agent(
        id=data.get("id", data.get("agent_id", "")),
        name=data.get("name", ""),
        version=data.get("version", ""),
        description=data.get("description", ""),
        protocol=data.get("protocol", ""),
        endpoint=data.get("endpoint", ""),
        capabilities=capabilities,
        trust_score=trust,
        tags=metadata.get("tags", []),
        verified=data.get("verified", False),
        owner_name=owner.get("name", ""),
        repository=metadata.get("repository", ""),
    )


def find_agent(
    skill: str = None,
    language: str = None,
    max_price: float = None,
    min_reputation: float = None,
    verified: bool = None,
    protocol: str = None,
    tags: list[str] = None,
    api_key: str = None,
) -> Optional[Agent]:
    """
    Find the best agent matching your criteria.

    Returns the highest-reputation agent that matches all filters.

    Example:
        agent = find_agent(
            skill="transcribe",
            language="zh",
            max_price=0.03,
            min_reputation=4.5,
            verified=True
        )
    """
    results = search_agents(
        skill=skill,
        language=language,
        max_price=max_price,
        min_reputation=min_reputation,
        verified=verified,
        protocol=protocol,
        tags=tags,
        limit=1,
        api_key=api_key,
    )
    return results.best()


def search_agents(
    skill: str = None,
    language: str = None,
    max_price: float = None,
    min_reputation: float = None,
    verified: bool = None,
    protocol: str = None,
    tags: list[str] = None,
    limit: int = 10,
    offset: int = 0,
    api_key: str = None,
) -> AgentSearchResult:
    """
    Search for agents by capability.

    Returns a list of matching agents sorted by trust score.

    Example:
        results = search_agents(skill="code-review", language="en")
        for agent in results.agents:
            print(f"{agent.name}: {agent.trust_score.total}/100")
    """
    with AgentDNAClient(api_key=api_key or "") as client:
        data = client.search(
            skill=skill,
            language=language,
            max_price=max_price,
            min_reputation=min_reputation,
            verified=verified,
            protocol=protocol,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    agents = [_parse_agent(a) for a in data.get("agents", [])]
    return AgentSearchResult(
        agents=agents,
        total=data.get("total", len(agents)),
        query=data.get("query", {}),
    )
