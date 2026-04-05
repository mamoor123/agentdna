#!/usr/bin/env python3
"""
🧬 AgentDNA CLI — Sentry for AI Agents

Usage:
    agentdna stats [func]                View observability stats
    agentdna stats --reset [func]        Reset stats
    agentdna stats --export json         Export stats
    agentdna search <query>              Search for agents
    agentdna register [path]             Register your agent
    agentdna init [name]                 Generate agentdna.yaml
    agentdna trust <agent-id>            View trust score
    agentdna status <agent-id>           Check agent health
    agentdna review <agent-id>           Submit a review
"""

import sys

import click

_CLI_VERSION = "0.2.0"


@click.group()
@click.version_option(version=_CLI_VERSION)
def cli():
    """🧬 AgentDNA — Sentry for AI Agents"""
    pass


# --- Stats Command (the money maker) ---

@cli.command()
@click.argument("func_name", required=False, default=None)
@click.option("--reset", is_flag=True, help="Reset stats for this function (or all)")
@click.option("--export", "export_format", type=click.Choice(["json", "csv"]), help="Export format")
@click.option("--db", "db_path", help="Path to SQLite database")
def stats(func_name, reset, export_format, db_path):
    """📊 View observability stats for your agents."""
    import os
    if db_path:
        os.environ["AGENTDNA_DB_PATH"] = db_path

    from agentdna.plugins.observe import get_stats, reset_stats, export_stats

    if reset:
        if func_name:
            reset_stats(func_name)
            click.echo(f"✅ Reset stats for: {func_name}")
        else:
            reset_stats()
            click.echo("✅ Reset all stats")
        return

    if export_format:
        output = export_stats(func_name, format=export_format)
        click.echo(output)
        return

    data = get_stats(func_name)

    if not data:
        click.echo("📊 No data yet. Add @observe to your agent functions first.")
        click.echo()
        click.echo("  from agentdna import observe")
        click.echo()
        click.echo("  @observe")
        click.echo("  def my_agent(prompt):")
        click.echo("      return result")
        return

    # Single function stats
    if func_name and isinstance(data, dict) and "total_calls" in data:
        _print_stats(func_name, data)
        return

    # All functions
    click.echo(f"\n📊 AgentDNA — {len(data)} observed function(s)\n")
    for name, s in data.items():
        _print_stats(name, s, compact=True)
    click.echo()


def _print_stats(name: str, s: dict, compact: bool = False):
    """Pretty-print stats for a function."""
    total = s.get("total_calls", 0)
    success_rate = s.get("success_rate", 0)
    avg_latency = s.get("avg_latency_ms", 0)
    p50 = s.get("p50_latency_ms", 0)
    p95 = s.get("p95_latency_ms", 0)
    p99 = s.get("p99_latency_ms", 0)
    failed = s.get("failed_calls", 0)
    errors = s.get("error_types", {})
    first = s.get("first_seen", "?")
    last = s.get("last_seen", "?")

    # Health indicator
    if success_rate >= 0.95:
        health = "✅ Healthy"
    elif success_rate >= 0.80:
        health = "⚠️  Degraded"
    else:
        health = "🔴 Unhealthy"

    if compact:
        bar = "█" * int(success_rate * 10) + "░" * (10 - int(success_rate * 10))
        click.echo(f"  📌 {name}")
        click.echo(f"     {health}  {total} calls  {bar} {success_rate:.0%}  avg {avg_latency:.0f}ms")
        if failed:
            click.echo(f"     ❌ {failed} failures: {', '.join(f'{k}({v})' for k, v in errors.items())}")
        click.echo()
    else:
        click.echo(f"\n📊 Stats: {name}")
        click.echo(f"{'━' * 45}")
        click.echo(f"  Health:           {health}")
        click.echo(f"  Total calls:      {total}")
        click.echo(f"  Success rate:     {success_rate:.1%}")
        click.echo(f"  Failed calls:     {failed}")
        click.echo(f"{'━' * 45}")
        click.echo(f"  Avg latency:      {avg_latency:.1f} ms")
        click.echo(f"  P50 latency:      {p50:.1f} ms")
        click.echo(f"  P95 latency:      {p95:.1f} ms")
        click.echo(f"  P99 latency:      {p99:.1f} ms")
        if errors:
            click.echo(f"{'━' * 45}")
            click.echo(f"  Errors:")
            for err_type, count in errors.items():
                click.echo(f"    {err_type}: {count}")
        click.echo(f"{'━' * 45}")
        click.echo(f"  First seen:       {first}")
        click.echo(f"  Last seen:        {last}")
        click.echo()


# --- Search Command ---

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


# --- Register Command ---

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


# --- Init Command ---

@cli.command()
@click.argument("name", default="MyAgent")
@click.option("--output", "-o", default="./agentdna.yaml", help="Output file path")
def init(name, output):
    """Generate a starter agentdna.yaml file."""
    from agentdna.registry import generate_agent_card

    path = generate_agent_card(name=name, output_path=output)
    click.echo(f"✅ Created agent card: {path}")
    click.echo("Edit it with your agent's details, then run: agentdna register")


# --- Trust Command ---

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


# --- Status Command ---

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


# --- Review Command ---

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
