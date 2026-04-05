# 🧬 AgentDNA — Sentry for AI Agents

**One-line observability for any Python agent.** No framework required. No API key. No network calls.

```bash
pip install agentdna
```

## Quick Start

```python
from agentdna import observe, get_stats

@observe
def my_agent(prompt):
    # your existing agent code
    return llm.call(prompt)

my_agent("hello world")

# View stats (persists across restarts)
print(get_stats())
```

That's it. One decorator. Full observability.

## What You Get

```
📊 Stats: my_agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Health:           ✅ Healthy
  Total calls:      42
  Success rate:     97.6%
  Failed calls:     1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Avg latency:      1250.5 ms
  P50 latency:      980.0 ms
  P95 latency:      2100.0 ms
  P99 latency:      3500.0 ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Errors:
    Timeout: 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Features

- **📊 Call tracking** — total calls, success/failure rates
- **⏱️ Latency** — avg, p50, p95, p99 percentiles
- **❌ Error tracking** — error types and frequency
- **💾 SQLite persistence** — data survives restarts
- **🔒 100% local** — no network calls, no API key
- **🐍 Sync & async** — works with both
- **🖥️ CLI included** — `agentdna stats`

## CLI

```bash
agentdna stats                    # overview of all observed functions
agentdna stats my_agent           # detailed view
agentdna stats --export json      # export as JSON
agentdna stats --export csv       # export as CSV
agentdna stats --reset            # clear all data
```

## Usage

### Basic

```python
from agentdna import observe

@observe
def my_agent(prompt):
    return llm.call(prompt)
```

### With Options

```python
@observe(name="transcriber", tags={"version": "2.0", "model": "whisper"})
def transcribe(audio_path):
    return whisper.transcribe(audio_path)
```

### Async Support

```python
@observe
async def my_async_agent(prompt):
    result = await llm.acall(prompt)
    return result
```

### Get Stats Programmatically

```python
from agentdna import get_stats

stats = get_stats("my_agent")
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"P95 latency: {stats['p95_latency_ms']:.0f}ms")

# All functions
all_stats = get_stats()
for name, s in all_stats.items():
    print(f"{name}: {s['total_calls']} calls")
```

### Export Stats

```python
from agentdna import export_stats

json_str = export_stats(format="json")
csv_str = export_stats(format="csv")
```

## How It Works

1. Decorator wraps your function
2. Each call logs: timestamp, success/failure, latency, input/output sizes, errors
3. Data batches to `~/.agentdna/observe.db` (SQLite, WAL mode)
4. Read stats anytime via `get_stats()` or `agentdna stats`

**No dependencies** beyond Python stdlib. `click` is only needed for the CLI.

## Data Location

Default: `~/.agentdna/observe.db`

Custom path:
```python
import os
os.environ["AGENTDNA_DB_PATH"] = "/path/to/my/observe.db"
```

## Why AgentDNA?

| Without AgentDNA | With AgentDNA |
|-----------------|---------------|
| `print("done!")` | Track every call with latency + errors |
| Hope nothing breaks | Know exactly when and what breaks |
| Debug blind | P95 latency, error breakdown, trends |
| Lose data on restart | SQLite persistence |

## Installation

```bash
pip install agentdna
```

Optional features:
```bash
pip install agentdna[discovery]   # agent discovery (httpx, PyYAML)
pip install agentdna[server]      # run registry server (FastAPI)
```

## License

Apache 2.0
