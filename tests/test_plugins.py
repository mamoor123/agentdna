"""Tests for framework plugins."""

import pytest
import asyncio

from agentdna.plugins.observe import observe, get_stats, _stats_registry


class TestObserveDecorator:
    def setup_method(self):
        """Clear stats registry between tests."""
        _stats_registry.clear()

    def test_sync_function_tracking(self):
        @observe
        def my_agent(prompt: str) -> str:
            return f"processed: {prompt}"

        result = my_agent("hello")
        assert result == "processed: hello"

        stats = get_stats("my_agent")
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["avg_latency_ms"] >= 0

    def test_sync_function_error_tracking(self):
        @observe
        def failing_agent(prompt: str) -> str:
            raise ValueError("Something went wrong")

        with pytest.raises(ValueError):
            failing_agent("test")

        stats = get_stats("failing_agent")
        assert stats["total_calls"] == 1
        assert stats["failed_calls"] == 1
        assert "ValueError" in stats["error_types"]

    def test_multiple_calls_accumulate(self):
        @observe
        def counter_agent(prompt: str) -> str:
            return "ok"

        counter_agent("a")
        counter_agent("b")
        counter_agent("c")

        stats = get_stats("counter_agent")
        assert stats["total_calls"] == 3
        assert stats["successful_calls"] == 3

    @pytest.mark.asyncio
    async def test_async_function_tracking(self):
        @observe
        async def async_agent(prompt: str) -> str:
            await asyncio.sleep(0.01)
            return f"async: {prompt}"

        result = await async_agent("hello")
        assert result == "async: hello"

        stats = get_stats("async_agent")
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1

    @pytest.mark.asyncio
    async def test_async_error_tracking(self):
        @observe
        async def async_failing_agent(prompt: str) -> str:
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError):
            await async_failing_agent("test")

        stats = get_stats("async_failing_agent")
        assert stats["failed_calls"] == 1

    def test_input_output_size_tracking(self):
        @observe
        def size_agent(prompt: str) -> str:
            return prompt * 3

        size_agent("abc")

        stats = get_stats("size_agent")
        assert stats["total_input_chars"] > 0
        assert stats["total_output_chars"] > 0
        assert stats["total_output_chars"] == stats["total_input_chars"] * 3

    def test_decorator_with_options(self):
        @observe(agent_id="dna:test:v1", track_cost=True)
        def configured_agent(prompt: str) -> str:
            return "ok"

        configured_agent("test")

        assert hasattr(configured_agent, "_agentdna_config")
        assert configured_agent._agentdna_config.agent_id == "dna:test:v1"
        assert configured_agent._agentdna_config.track_cost is True

    def test_get_all_stats(self):
        @observe
        def agent_a(prompt: str) -> str:
            return "a"

        @observe
        def agent_b(prompt: str) -> str:
            return "b"

        agent_a("test")
        agent_b("test")

        all_stats = get_stats()
        assert "agent_a" in all_stats
        assert "agent_b" in all_stats

    def test_get_stats_nonexistent(self):
        assert get_stats("nonexistent") == {}
