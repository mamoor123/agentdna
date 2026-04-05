"""
AgentDNA Observe Decorator — One-line integration for any agent

Drop-in decorator that works with ANY Python agent code.
No framework required.

Usage:
    from agentdna.plugins.observe import observe

    @observe
    def my_agent(prompt):
        # your existing agent code
        return result

    # Or with options:
    @observe(agent_id="dna:my-agent:v1", track_cost=True)
    async def my_async_agent(prompt):
        return await agent.run(prompt)

What it tracks:
- Call count and success/failure rate
- Latency per call
- Input/output sizes
- Error types and frequency
"""

from __future__ import annotations

import functools
import time
from typing import Callable


class ObserveConfig:
    """Configuration for the observe decorator."""

    def __init__(
        self,
        agent_id: str = None,
        api_key: str = None,
        track_cost: bool = False,
        sample_rate: float = 1.0,  # 1.0 = track everything
        tags: dict = None,
    ):
        self.agent_id = agent_id
        self.api_key = api_key
        self.track_cost = track_cost
        self.sample_rate = sample_rate
        self.tags = tags or {}


class ObserveStats:
    """Accumulates statistics for an observed function."""

    def __init__(self):
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_latency_ms = 0.0
        self.total_input_chars = 0
        self.total_output_chars = 0
        self.errors: dict[str, int] = {}  # error_type -> count

    def record_success(self, latency_ms: float, input_size: int = 0, output_size: int = 0):
        self.total_calls += 1
        self.successful_calls += 1
        self.total_latency_ms += latency_ms
        self.total_input_chars += input_size
        self.total_output_chars += output_size

    def record_failure(self, latency_ms: float, error: Exception):
        self.total_calls += 1
        self.failed_calls += 1
        self.total_latency_ms += latency_ms
        error_type = type(error).__name__
        self.errors[error_type] = self.errors.get(error_type, 0) + 1

    def to_dict(self) -> dict:
        avg_latency = (
            self.total_latency_ms / self.total_calls if self.total_calls > 0 else 0
        )
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": (
                self.successful_calls / self.total_calls if self.total_calls > 0 else 0
            ),
            "avg_latency_ms": round(avg_latency, 2),
            "total_latency_ms": round(self.total_latency_ms, 2),
            "total_input_chars": self.total_input_chars,
            "total_output_chars": self.total_output_chars,
            "error_types": self.errors,
        }


# Global stats registry
_stats_registry: dict[str, ObserveStats] = {}


def get_stats(func_name: str = None) -> dict:
    """
    Get statistics for observed functions.

    Example:
        stats = get_stats("my_agent")
        print(f"Success rate: {stats['success_rate']:.1%}")
    """
    if func_name:
        stats = _stats_registry.get(func_name)
        return stats.to_dict() if stats else {}
    return {name: stats.to_dict() for name, stats in _stats_registry.items()}


def observe(func: Callable = None, **config_kwargs):
    """
    Decorator to observe any agent function.

    Can be used as:
        @observe
        def my_agent(prompt): ...

    Or with options:
        @observe(agent_id="dna:my-agent:v1", track_cost=True)
        def my_agent(prompt): ...
    """
    if func is None:
        # Called with arguments: @observe(...)
        return functools.partial(observe, **config_kwargs)

    config = ObserveConfig(**config_kwargs)
    stats = ObserveStats()
    _stats_registry[func.__name__] = stats

    if functools.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            input_size = sum(len(str(a)) for a in args) + sum(len(str(v)) for v in kwargs.values())

            try:
                result = await func(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                output_size = len(str(result)) if result else 0
                stats.record_success(elapsed, input_size, output_size)
                return result
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                stats.record_failure(elapsed, e)
                raise

        async_wrapper._agentdna_stats = stats
        async_wrapper._agentdna_config = config
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            input_size = sum(len(str(a)) for a in args) + sum(len(str(v)) for v in kwargs.values())

            try:
                result = func(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                output_size = len(str(result)) if result else 0
                stats.record_success(elapsed, input_size, output_size)
                return result
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                stats.record_failure(elapsed, e)
                raise

        sync_wrapper._agentdna_stats = stats
        sync_wrapper._agentdna_config = config
        return sync_wrapper
