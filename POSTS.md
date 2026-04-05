# Launch Posts

## Twitter/X (pick one)

### Short post:
> Built a one-line observability decorator for AI agents.
> 
> ```python
> @observe
> def my_agent(prompt):
>     return llm.call(prompt)
> ```
> 
> Tracks calls, latency percentiles, errors. Persists to SQLite. Zero dependencies.
> 
> `pip install agentdna-sdk`
> 
> [attach 15-sec demo GIF]

### Thread post:
> 🧵 I was debugging my AI agent pipeline blind. No visibility into what was failing, how slow things were, or which agent was the bottleneck.
> 
> So I built a one-line decorator:
> 
> ```python
> from agentdna import observe, get_stats
> 
> @observe
> def my_agent(prompt):
>     return llm.call(prompt)
> ```
> 
> That's it. Now I get:
> - ✅ Success/failure rates
> - ⏱️ P50/P95/P99 latency
> - ❌ Error type breakdown
> - 💾 All persisted to local SQLite
> 
> No API key. No server. No network calls.
> 
> Works with sync and async. Works with any framework.
> 
> pip install agentdna-sdk
> 
> [attach demo video]

## Reddit (r/MachineLearning or r/LocalLLaMA)

**Title:** I built a one-line observability decorator for AI agents (SQLite, zero deps)

**Body:**

I was building agent pipelines and had zero visibility into what was happening. Which agent was slow? Which was failing? How often?

Existing tools (LangSmith, Phoenix, etc.) are great but they're heavy — require accounts, API keys, cloud connections. I wanted something that just works locally.

So I built AgentDNA:

```python
from agentdna import observe

@observe
def transcribe(audio):
    return whisper.transcribe(audio)
```

What it tracks:
- Call count + success/failure rates
- Latency percentiles (p50, p95, p99)
- Error types and frequency
- All persisted to local SQLite (~/.agentdna/observe.db)

CLI included:

```
$ agentdna stats

📊 AgentDNA — 3 observed function(s)

  📌 transcriber
     ✅ Healthy  42 calls  ██████████ 97%  avg 1250ms
  📌 summarizer
     ⚠️  Degraded  38 calls  █████████░ 92%  avg 3400ms
     ❌ 3 failures: Timeout(2), RateLimit(1)
```

Zero dependencies beyond Python stdlib. Works with any code — LangChain, CrewAI, raw OpenAI, anything.

PyPI: `pip install agentdna-sdk`
GitHub: https://github.com/mamoor123/agentdna

Would love feedback. Is this useful to anyone else?
