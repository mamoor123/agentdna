#!/usr/bin/env python3
"""
🧬 AgentDNA CLI — DNS for AI Agents

Usage:
    agentdna search <query>              Search for agents
    agentdna register [path]             Register your agent
    agentdna init [name]                 Generate agentdna.yaml
    agentdna trust <agent-id>            View trust score
    agentdna status <agent-id>           Check agent health
    agentdna review <agent-id>           Submit a review
"""

import sys

import click

_CLI_VERSION = "0.1.0"


@click.group()
@click.version_option(version=_CLI_VERSION)
def cli():
    """🧬 AgentDNA — DNS for AI Agents"""
    pass


@cli.command()
@click.argument("query")
@click.option("--language", "-l", help="Filter by language (e.g., en, zh)")
@click.option("--max-price", "-p", type=float, help="Maximum price per unit")
@click.option("--min-trust", "-t", type=float, help="Minimum trust score (0-100)")
@click.option("--verified", is_flag=True, help="Only show verified agents")
@click.option("--protocol", type=click.Choice(["a2a", "mcp", "any"]), default="any")
@click.option("--limit", "-n", default=10, help="Number of results")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def search(query, language, max_price, min_trust, verified, protocol, limit, output_json):
    """Search for agents by capability."""
    from agentdna.discovery import search_agents

    results = search_agents(
        skill=query,
        language=language,
        max_price=max_price,
        min_reputation=min_trust,
        verified=verified,
        protocol=protocol if protocol != "any" else None,
        limit=limit,
    )

    if output_json:
        import json
        from dataclasses import asdict
        click.echo(json.dumps([asdict(a) for a in results.agents], indent=2, default=str))
        return

    if not results.agents:
        click.echo(f"No agents found for: {query}")
        return

    click.echo(f"\n🧬 Found {results.total} agents for '{query}':\n")
    for agent in results.agents:
        score = agent.trust_score.total if agent.trust_score else "?"
        verified_badge = " 🏆" if agent.verified else ""
        click.echo(f"  {agent.name} v{agent.version}  (DNA: {score}/100){verified_badge}")
        click.echo(f"  ID: {agent.id}")
        click.echo(f"  {agent.description}")
        for cap in agent.capabilities:
            price = cap.pricing.display() if cap.pricing else "N/A"
            langs = ", ".join(cap.languages) if cap.languages else "any"
            click.echo(f"    → {cap.skill} ({price}) [{langs}]")
        click.echo()


@cli.command()
@click.argument("path", default="./agentdna.yaml")
def register(path):
    """Register your agent in the AgentDNA registry."""
    from agentdna.registry import register_agent

    try:
        result = register_agent(path)
        click.echo(f"✅ Registered: {result.get('agent_id', 'success')}")
    except FileNotFoundError:
        click.echo(f"❌ File not found: {path}")
        click.echo("Run 'agentdna init' to create one.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Registration failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("name", default="MyAgent")
@click.option("--output", "-o", default="./agentdna.yaml", help="Output file path")
def init(name, output):
    """Generate a starter agentdna.yaml file."""
    from agentdna.registry import generate_agent_card

    path = generate_agent_card(name=name, output_path=output)
    click.echo(f"✅ Created agent card: {path}")
    click.echo("Edit it with your agent's details, then run: agentdna register")


@cli.command()
@click.argument("agent_id")
def trust(agent_id):
    """View the trust score for an agent."""
    from agentdna.client import AgentDNAClient

    with AgentDNAClient() as client:
        score = client.get_trust_score(agent_id)

    click.echo(f"\n🧬 Trust Score: {agent_id}\n")
    click.echo(f"  Total:                {score.get('total', 0)}/100")
    click.echo(f"  Task Completion:      {score.get('task_completion', 0)}/40")
    click.echo(f"  Response Quality:     {score.get('response_quality', 0)}/25")
    click.echo(f"  Latency Reliability:  {score.get('latency_reliability', 0)}/15")
    click.echo(f"  Uptime:               {score.get('uptime_score', 0)}/10")
    click.echo(f"  Verification:         {score.get('verification_bonus', 0)}/10")


@cli.command()
@click.argument("agent_id")
def status(agent_id):
    """Check agent health status."""
    from agentdna.client import AgentDNAClient

    with AgentDNAClient() as client:
        info = client.get_agent(agent_id)

    click.echo(f"\n🧬 Agent Status: {agent_id}\n")
    click.echo(f"  Name:     {info.get('name', 'Unknown')}")
    click.echo(f"  Version:  {info.get('version', 'Unknown')}")
    click.echo(f"  Status:   {'🟢 Online' if info.get('online') else '🔴 Offline'}")
    click.echo(f"  Uptime:   {info.get('uptime', 'Unknown')}")
    click.echo(f"  Tasks:    {info.get('total_tasks_completed', 0)} completed")


@cli.command()
@click.argument("agent_id")
@click.option("--rating", "-r", type=click.IntRange(1, 5), prompt="Rating (1-5)")
@click.option("--comment", "-c", prompt="Review comment")
def review(agent_id, rating, comment):
    """Submit a review for an agent."""
    from agentdna.client import AgentDNAClient

    with AgentDNAClient() as client:
        client.submit_review(agent_id, rating, comment)

    click.echo(f"✅ Review submitted for {agent_id}")


if __name__ == "__main__":
    cli()
