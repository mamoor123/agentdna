"""Task marketplace — hire agents with escrow."""

import asyncio

from agentdna.client import AgentDNAClient
from agentdna.models import TaskResult


async def hire_agent(
    agent: str,
    task: str,
    input_file: str = None,
    input_url: str = None,
    input_text: str = None,
    max_price: float = None,
    currency: str = "USD",
    timeout: str = "5m",
    escrow: bool = True,
    api_key: str = None,
    poll_interval: float = 2.0,
) -> TaskResult:
    """
    Hire an agent to complete a task.

    Supports async polling — waits for task completion by default.

    Example:
        result = await hire_agent(
            agent="dna:transcribe-pro:v2.1",
            task="Transcribe this meeting recording",
            input_file="meeting.wav",
            max_price=1.50,
            escrow=True,
        )
        print(result.output)

    Note:
        Uses synchronous HTTP client internally. For high-concurrency async
        workloads, use hire_agent_sync in a thread executor instead.
    """
    task_payload = {
        "description": task,
        "max_price": max_price,
        "currency": currency,
        "timeout": timeout,
        "escrow": escrow,
    }

    if input_file:
        task_payload["input"] = {"type": "file", "path": input_file}
    elif input_url:
        task_payload["input"] = {"type": "url", "url": input_url}
    elif input_text:
        task_payload["input"] = {"type": "text", "content": input_text}

    client = AgentDNAClient(api_key=api_key or "")
    try:
        # Create the task (sync call — use run_in_executor for true async)
        result = client.create_task(agent, task_payload)
        task_id = result["task_id"]

        # Poll for completion
        while True:
            status = client.get_task(task_id)
            task_status = status.get("status", "pending")

            if task_status in ("completed", "failed", "refunded"):
                return TaskResult(
                    task_id=task_id,
                    agent_id=agent,
                    status=task_status,
                    output=status.get("output"),
                    cost=status.get("cost", 0.0),
                    currency=status.get("currency", "USD"),
                    duration_seconds=status.get("duration_seconds", 0.0),
                    error=status.get("error"),
                )

            await asyncio.sleep(poll_interval)
    finally:
        client.close()


def hire_agent_sync(*args, **kwargs) -> TaskResult:
    """Synchronous wrapper for hire_agent."""
    return asyncio.run(hire_agent(*args, **kwargs))
