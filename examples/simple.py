"""
Simplest AgentDNA example — just 3 lines of code.

    pip install agentdna-sdk
    python simple.py
"""

from agentdna import observe, get_stats


@observe
def my_agent(prompt: str) -> str:
    """Your agent. Any code works."""
    return f"Processed: {prompt}"


# Use your agent normally
my_agent("hello")
my_agent("world")
my_agent("this is tracked automatically")

# Check stats
print(get_stats())
