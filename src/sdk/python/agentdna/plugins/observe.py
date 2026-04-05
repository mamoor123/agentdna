"""
AgentDNA Observe — Sentry for AI Agents

One-line decorator that works with ANY Python agent code.
No framework required. Stats persist to local SQLite.

Usage:
    from agentdna import observe, get_stats

    @observe
    def my_agent(prompt):
        # your existing agent code
        return result

    # Or with options:
    @observe(name="my-agent", tags={"version": "2.0"})
    async def my_async_agent(prompt):
        return await agent.run(prompt)

    # View stats anytime (even after restart)
    print(get_stats("my_agent"))

What it tracks:
- Call count and success/failure rate
- Latency per call (avg, p50, p95, p99)
- Input/output sizes
- Error types and frequency
- Timestamp of last call

Data is stored locally in ~/.agentdna/observe.db (SQLite).
No network calls. No API key needed. Works offline.
"""

from __future__ import annotations

import atexit
import asyncio
import functools
import json
import os
import signal
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


# --- SQLite Storage ---

def _get_db_path() -> Path:
    """Get path to the local SQLite database."""
    custom = os.environ.get("AGENTDNA_DB_PATH")
    if custom:
        return Path(custom)
    return Path.home() / ".agentdna" / "observe.db"


def _get_db() -> sqlite3.Connection:
    """Get or create the SQLite connection with WAL mode for performance."""
    path = _get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection):
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS functions (
            name TEXT PRIMARY KEY,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            total_calls INTEGER DEFAULT 0,
            successful_calls INTEGER DEFAULT 0,
            failed_calls INTEGER DEFAULT 0,
            total_latency_ms REAL DEFAULT 0,
            total_input_chars INTEGER DEFAULT 0,
            total_output_chars INTEGER DEFAULT 0,
            errors TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            func_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            success INTEGER NOT NULL,
            latency_ms REAL NOT NULL,
            input_chars INTEGER DEFAULT 0,
            output_chars INTEGER DEFAULT 0,
            error_type TEXT,
            tags TEXT DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_calls_func_time
            ON calls(func_name, timestamp);
    """)


def _upsert_function(conn: sqlite3.Connection, name: str, success: bool,
                     latency_ms: float, input_chars: int, output_chars: int,
                     error_type: Optional[str] = None):
    """Update aggregate stats for a function."""
    now = datetime.now(timezone.utc).isoformat()

    # Get current errors
    row = conn.execute("SELECT errors FROM functions WHERE name = ?", (name,)).fetchone()
    if row:
        errors = json.loads(row[0])
        if error_type:
            errors[error_type] = errors.get(error_type, 0) + 1

        conn.execute("""
            UPDATE functions SET
                last_seen = ?,
                total_calls = total_calls + 1,
                successful_calls = successful_calls + ?,
                failed_calls = failed_calls + ?,
                total_latency_ms = total_latency_ms + ?,
                total_input_chars = total_input_chars + ?,
                total_output_chars = total_output_chars + ?,
                errors = ?
            WHERE name = ?
        """, (now, 1 if success else 0, 0 if success else 1,
              latency_ms, input_chars, output_chars,
              json.dumps(errors), name))
    else:
        errors = {error_type: 1} if error_type else {}
        conn.execute("""
            INSERT INTO functions
                (name, first_seen, last_seen, total_calls, successful_calls,
                 failed_calls, total_latency_ms, total_input_chars, total_output_chars, errors)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
        """, (name, now, now,
              1 if success else 0, 0 if success else 1,
              latency_ms, input_chars, output_chars,
              json.dumps(errors)))


def _record_call(conn: sqlite3.Connection, name: str, success: bool,
                latency_ms: float, input_chars: int, output_chars: int,
                error_type: Optional[str] = None, tags: Optional[dict] = None):
    """Record an individual call for percentile calculations."""
    conn.execute("""
        INSERT INTO calls (func_name, timestamp, success, latency_ms,
                          input_chars, output_chars, error_type, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, datetime.now(timezone.utc).isoformat(),
          1 if success else 0, latency_ms,
          input_chars, output_chars, error_type,
          json.dumps(tags or {})))


# --- In-Memory Cache (for hot path performance) ---

class _HotCache:
    """In-memory cache that batches writes to SQLite."""

    def __init__(self, flush_every_n: int = 10):
        self._calls: list[tuple] = []
        self._flush_every = flush_every_n
        self._conn: Optional[sqlite3.Connection] = None

    def _ensure_conn(self):
        if self._conn is None:
            self._conn = _get_db()
        return self._conn

    def record(self, name: str, success: bool, latency_ms: float,
               input_chars: int, output_chars: int,
               error_type: Optional[str] = None, tags: Optional[dict] = None):
        """Record a call. Flushes to SQLite periodically."""
        self._calls.append((name, success, latency_ms, input_chars, output_chars, error_type, tags))

        if len(self._calls) >= self._flush_every:
            self.flush()

    def flush(self):
        """Write all buffered calls to SQLite."""
        if not self._calls:
            return

        conn = self._ensure_conn()
        try:
            for call in self._calls:
                name, success, latency_ms, input_chars, output_chars, error_type, tags = call
                _upsert_function(conn, name, success, latency_ms, input_chars, output_chars, error_type)
                _record_call(conn, name, success, latency_ms, input_chars, output_chars, error_type, tags)
            conn.commit()
        except Exception:
            pass  # Don't let DB errors break the observed function
        self._calls.clear()

    def close(self):
        """Flush and close."""
        self.flush()
        if self._conn:
            self._conn.close()
            self._conn = None


# Global hot cache
_cache = _HotCache(flush_every_n=5)

# Ensure buffered calls are flushed on clean exit
atexit.register(_cache.close)

def _signal_handler(signum, frame):
    _cache.close()
    # Re-raise with default handler so the process exits with the correct signal
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)

for _sig in (signal.SIGTERM, signal.SIGINT):
    try:
        signal.signal(_sig, _signal_handler)
    except (OSError, ValueError):
        pass  # Not all signals are available on all platforms / non-main threads


# --- Stats Retrieval ---

def get_stats(func_name: Optional[str] = None) -> dict:
    """
    Get statistics for observed functions from SQLite.

    Args:
        func_name: Specific function name, or None for all functions.

    Returns:
        Dict with stats. Example:
            {
                "total_calls": 42,
                "success_rate": 0.97,
                "avg_latency_ms": 1250.5,
                "p50_latency_ms": 980.0,
                "p95_latency_ms": 2100.0,
                "p99_latency_ms": 3500.0,
                "error_types": {"ValueError": 1, "Timeout": 1},
                "first_seen": "2026-04-05T...",
                "last_seen": "2026-04-05T..."
            }
    """
    # Flush any pending writes first
    _cache.flush()

    conn = _get_db()
    try:
        if func_name:
            return _get_stats_for(conn, func_name)
        else:
            rows = conn.execute("SELECT name FROM functions ORDER BY last_seen DESC").fetchall()
            return {row[0]: _get_stats_for(conn, row[0]) for row in rows}
    finally:
        conn.close()


def _get_stats_for(conn: sqlite3.Connection, func_name: str) -> dict:
    """Get detailed stats for a single function."""
    row = conn.execute(
        "SELECT * FROM functions WHERE name = ?", (func_name,)
    ).fetchone()

    if not row:
        return {}

    # row: name(0), first_seen(1), last_seen(2), total_calls(3),
    #      successful_calls(4), failed_calls(5), total_latency_ms(6),
    #      total_input_chars(7), total_output_chars(8), errors(9)
    total = row[3]
    success_rate = row[4] / total if total > 0 else 0
    avg_latency = row[6] / total if total > 0 else 0

    # Get latency percentiles from calls table
    latencies = conn.execute(
        "SELECT latency_ms FROM calls WHERE func_name = ? ORDER BY latency_ms",
        (func_name,)
    ).fetchall()

    lat_values = [l[0] for l in latencies]

    def percentile(values: list[float], p: int) -> float:
        """Calculate percentile using linear interpolation (same method as numpy)."""
        if not values:
            return 0
        if len(values) == 1:
            return values[0]
        k = (len(values) - 1) * p / 100
        f = int(k)
        c = f + 1
        if c >= len(values):
            return values[f]
        return values[f] + (k - f) * (values[c] - values[f])

    return {
        "total_calls": total,
        "successful_calls": row[4],
        "failed_calls": row[5],
        "success_rate": round(success_rate, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "p50_latency_ms": round(percentile(lat_values, 50), 2),
        "p95_latency_ms": round(percentile(lat_values, 95), 2),
        "p99_latency_ms": round(percentile(lat_values, 99), 2),
        "total_input_chars": row[7],
        "total_output_chars": row[8],
        "error_types": json.loads(row[9]) if row[9] else {},
        "first_seen": row[1],
        "last_seen": row[2],
    }


def reset_stats(func_name: Optional[str] = None):
    """
    Clear stats for a function (or all functions if name is None).

    Warning: This permanently deletes the data.
    """
    _cache.flush()
    conn = _get_db()
    try:
        if func_name:
            conn.execute("DELETE FROM functions WHERE name = ?", (func_name,))
            conn.execute("DELETE FROM calls WHERE func_name = ?", (func_name,))
        else:
            conn.execute("DELETE FROM functions")
            conn.execute("DELETE FROM calls")
        conn.commit()
    finally:
        conn.close()


def export_stats(func_name: Optional[str] = None, format: str = "json") -> str:
    """
    Export stats as JSON or CSV.

    Args:
        func_name: Specific function or None for all.
        format: "json" or "csv"
    """
    stats = get_stats(func_name)

    if format == "json":
        return json.dumps(stats, indent=2, default=str)

    if format == "csv":
        if not stats:
            return ""
        # Flatten for CSV
        lines = ["name,total_calls,success_rate,avg_latency_ms,p95_latency_ms,failed_calls,error_types"]
        items = stats.items() if isinstance(stats, dict) and "total_calls" not in stats else [(func_name or "unknown", stats)]
        for name, s in items:
            lines.append(f"{name},{s.get('total_calls',0)},{s.get('success_rate',0)},{s.get('avg_latency_ms',0)},{s.get('p95_latency_ms',0)},{s.get('failed_calls',0)},\"{s.get('error_types',{})}\"")
        return "\n".join(lines)

    return json.dumps(stats, indent=2, default=str)


# --- Decorator ---

class ObserveConfig:
    """Configuration for the observe decorator."""

    def __init__(
        self,
        name: Optional[str] = None,
        agent_id: Optional[str] = None,
        track_cost: bool = False,
        sample_rate: float = 1.0,
        tags: Optional[dict] = None,
    ):
        self.name = name
        self.agent_id = agent_id  # kept for backwards compat
        self.track_cost = track_cost
        self.sample_rate = sample_rate
        self.tags = tags or {}


def observe(func: Optional[Callable] = None, **config_kwargs):
    """
    Decorator to observe any agent function.

    Can be used as:
        @observe
        def my_agent(prompt): ...

    Or with options:
        @observe(name="my-agent", tags={"version": "2.0"})
        def my_agent(prompt): ...

    Data persists to ~/.agentdna/observe.db (SQLite).
    No network calls. Works offline.
    """
    if func is None:
        return functools.partial(observe, **config_kwargs)

    config = ObserveConfig(**config_kwargs)
    func_name = config.name or func.__name__

    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            input_size = sum(len(str(a)) for a in args) + sum(len(str(v)) for v in kwargs.values())

            try:
                result = await func(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                output_size = len(str(result)) if result else 0
                _cache.record(func_name, True, elapsed, input_size, output_size, tags=config.tags)
                return result
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                _cache.record(func_name, False, elapsed, input_size, 0,
                             error_type=type(e).__name__, tags=config.tags)
                raise

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
                _cache.record(func_name, True, elapsed, input_size, output_size, tags=config.tags)
                return result
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                _cache.record(func_name, False, elapsed, input_size, 0,
                             error_type=type(e).__name__, tags=config.tags)
                raise

        sync_wrapper._agentdna_config = config
        return sync_wrapper
