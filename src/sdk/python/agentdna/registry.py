"""Agent registration and card management."""

import os
from pathlib import Path
from typing import Optional

import yaml

from agentdna.client import AgentDNAClient


def load_agent_card(path: str = "./agentdna.yaml") -> dict:
    """
    Load and validate an agentdna.yaml file.

    Example:
        card = load_agent_card("./agentdna.yaml")
        print(card["agent"]["name"])
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Agent card not found: {path}")

    with open(file_path) as f:
        data = yaml.safe_load(f)

    if not data or "agent" not in data:
        raise ValueError("Invalid agentdna.yaml: missing 'agent' key")

    _validate_card(data["agent"])
    return data


def _validate_card(agent: dict) -> None:
    """Basic validation of agent card."""
    required = ["name", "version", "description", "protocol", "endpoint"]
    missing = [k for k in required if k not in agent]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    if agent["protocol"] not in ("a2a", "mcp", "custom"):
        raise ValueError(f"Invalid protocol: {agent['protocol']}. Must be a2a, mcp, or custom.")

    if not agent.get("capabilities"):
        raise ValueError("Agent must have at least one capability.")


def register_agent(
    path: str = "./agentdna.yaml",
    api_key: str = None,
) -> dict:
    """
    Register an agent in the AgentDNA registry.

    Example:
        result = register_agent("./agentdna.yaml")
        print(f"Registered: {result['agent_id']}")
    """
    card = load_agent_card(path)

    with AgentDNAClient(api_key=api_key or "") as client:
        result = client.register(card)

    return result


def generate_agent_card(
    name: str,
    version: str = "1.0.0",
    description: str = "",
    protocol: str = "a2a",
    endpoint: str = "",
    skills: list[dict] = None,
    output_path: str = "./agentdna.yaml",
) -> str:
    """
    Generate a starter agentdna.yaml file.

    Example:
        generate_agent_card(
            name="MyAgent",
            description="Does amazing things",
            endpoint="https://my-agent.example.com/a2a",
            skills=[{"skill": "summarize", "inputs": ["text/plain"]}],
        )
    """
    card = {
        "agent": {
            "name": name,
            "version": version,
            "description": description or f"{name} — an AI agent",
            "protocol": protocol,
            "endpoint": endpoint or f"https://{name.lower().replace(' ', '-')}.example.com/{protocol}",
            "capabilities": skills or [
                {
                    "skill": "default",
                    "description": "Default capability",
                    "inputs": ["text/plain"],
                    "output": "text/plain",
                    "languages": ["en"],
                    "pricing": {
                        "model": "free",
                        "amount": 0,
                        "currency": "USD",
                    },
                }
            ],
            "metadata": {
                "framework": "custom",
                "tags": [],
            },
            "security": {
                "data_handling": "temporary",
                "encryption": True,
            },
        }
    }

    output = Path(output_path)
    with open(output, "w") as f:
        yaml.dump(card, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return str(output.resolve())
