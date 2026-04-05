"""
🧬 AgentDNA — Sentry for AI Agents

One-line observability for any Python agent.
No framework required. No API key. No network calls.

Usage:
    from agentdna import observe, get_stats

    @observe
    def my_agent(prompt):
        return llm.call(prompt)

    # Check stats anytime (persists across restarts)
    print(get_stats())

    # Or use the CLI:
    #   agentdna stats
    #   agentdna stats my_agent
"""

__version__ = "0.2.0"

# ⭐ Primary exports — zero dependencies (uses only stdlib sqlite3)
from agentdna.plugins.observe import observe, get_stats, reset_stats, export_stats

# Everything else is lazy-imported to avoid requiring httpx/PyYAML
# for users who only want observability.


def __getattr__(name: str):
    """Lazy imports — only load when actually used."""
    _lazy = {
        # Models
        "Agent": ("agentdna.models", "Agent"),
        "AgentSearchResult": ("agentdna.models", "AgentSearchResult"),
        "Capability": ("agentdna.models", "Capability"),
        "Pricing": ("agentdna.models", "Pricing"),
        "TrustScore": ("agentdna.models", "TrustScore"),
        "TaskResult": ("agentdna.models", "TaskResult"),
        # Registry
        "register_agent": ("agentdna.registry", "register_agent"),
        "load_agent_card": ("agentdna.registry", "load_agent_card"),
        "generate_agent_card": ("agentdna.registry", "generate_agent_card"),
        # Discovery
        "find_agent": ("agentdna.discovery", "find_agent"),
        "search_agents": ("agentdna.discovery", "search_agents"),
        # Marketplace
        "hire_agent": ("agentdna.marketplace", "hire_agent"),
        "hire_agent_sync": ("agentdna.marketplace", "hire_agent_sync"),
        # Client
        "AgentDNAClient": ("agentdna.client", "AgentDNAClient"),
    }

    if name in _lazy:
        module_path, attr_name = _lazy[name]
        from importlib import import_module
        mod = import_module(module_path)
        return getattr(mod, attr_name)

    raise AttributeError(f"module 'agentdna' has no attribute {name!r}")


__all__ = [
    # ⭐ Core — observability (zero dependencies)
    "observe",
    "get_stats",
    "reset_stats",
    "export_stats",
    # Everything else (lazy, requires httpx/PyYAML)
    "AgentDNAClient",
    "Agent",
    "AgentSearchResult",
    "Capability",
    "Pricing",
    "TrustScore",
    "TaskResult",
    "register_agent",
    "load_agent_card",
    "generate_agent_card",
    "find_agent",
    "search_agents",
    "hire_agent",
    "hire_agent_sync",
]
