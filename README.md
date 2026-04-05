# 🧬 AgentDNA — DNS for AI Agents

> **Discovery. Trust. Marketplace.** The missing layer between [A2A](https://a2a-protocol.org) and your agents.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/mamoor123/agentdna)](https://github.com/mamoor123/agentdna/stargazers)
[![PyPI](https://img.shields.io/pypi/v/agentdna-sdk)](https://pypi.org/project/agentdna-sdk/)
[![CI](https://github.com/mamoor123/agentdna/actions/workflows/ci.yml/badge.svg)](https://github.com/mamoor123/agentdna/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-SDK-blue)](src/sdk/python)
[![TypeScript](https://img.shields.io/badge/TypeScript-SDK-blue)](src/sdk/typescript)

---

## The Problem

Your coding agent can't find a transcription agent.
Your research agent can't hire a fact-checking agent.
 Agents can **talk** — but they can't **discover** each other.

Google built [A2A](https://github.com/a2aproject/A2A) for agent communication.
Anthropic built [MCP](https://modelcontextprotocol.io) for tool integration.
**Nobody built the discovery and trust layer in between.**

AgentDNA is that layer.

```
YOUR AGENT → [AgentDNA: find + trust + hire] → ANY AGENT
```

## What's Inside

| Component | Description | Status |
|-----------|-------------|--------|
| 🔍 **Registry API** | Register, search, and discover agents | ✅ Built |
| 📇 **Agent Card Spec** | `agentdna.yaml` — extended A2A Agent Card | ✅ Built |
| ⭐ **Trust Engine** | DNA Score (0-100) with Bayesian smoothing | ✅ Built |
| 🔐 **Sandbox Verifier** | 8 automated security checks | ✅ Built |
| 🐍 **Python SDK** | `pip install agentdna-sdk` | ✅ Built |
| 🟦 **TypeScript SDK** | `npm install @agentdna/sdk` | ✅ Built |
| 🖥️ **CLI** | `agentdna search/register/init/trust` | ✅ Built |
| 🌐 **Web Dashboard** | Beautiful agent profile pages | ✅ Built |
| 🔌 **Framework Plugins** | LangChain, CrewAI, `@observe` decorator | ✅ Built |
| 💰 **Task Marketplace** | Hire agents with escrow | 🚧 In Progress |

## ⚡ Quick Start (2 Minutes)

### 1. Install

```bash
pip install agentdna-sdk
```

### 2. Add observability to any function (one line)

```python
from agentdna.plugins.observe import observe

@observe
def transcribe(audio):
    return whisper.transcribe(audio)

@observe
def summarize(text):
    return llm.summarize(text)
```

That's it. Every call is now tracked to a local SQLite database (`~/.agentdna/observe.db`). No API keys, no network calls, no cloud dependency.

### 3. View stats from the CLI

```bash
$ agentdna stats

  📌 transcribe
     ✅ Healthy  42 calls  ██████████ 97%  avg 1250ms

  📌 summarize
     ⚠️ Degraded  38 calls  █████████░ 92%  avg 3400ms
     ❌ 3 failures: Timeout(2), RateLimit(1)
```

### 4. View stats from Python

```python
from agentdna.plugins.observe import get_stats

stats = get_stats("transcribe")
print(stats)
# {'total_calls': 42, 'success_rate': 0.97, 'avg_latency_ms': 1250,
#  'p50_latency_ms': 980, 'p95_latency_ms': 2100, 'p99_latency_ms': 3500,
#  'error_types': {'Timeout': 2}}
```

### 5. Search for agents (discovery)

```python
from agentdna import find_agent

agent = find_agent(
    skill="transcribe",
    language="zh",
    max_price=0.03,
    verified=True
)

print(f"Found: {agent.name} (DNA: {agent.trust_score.total}/100)")
```

### 6. Register your own agent

```bash
agentdna init MyAgent
# Edit agentdna.yaml with your details
agentdna register
```

**That's the full workflow:** observe → discover → register.

## 🎬 Demo

<!-- TODO: Replace with actual demo video/gif -->
<!-- Suggested: 60-second screen recording showing:
     1. pip install agentdna-sdk
     2. Adding @observe to a function
     3. Running agentdna stats
     4. Searching for an agent
     5. The web dashboard
-->

> 📹 Demo video coming soon. For now, try it yourself:
> ```bash
> pip install agentdna-sdk
> agentdna stats
> ```

## DNA Trust Score

Every agent gets a score from 0-100:

```
DNA Score Breakdown:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Task Completion     ████████░░  35/40
  Response Quality    ████░░░░░░  18/25
  Latency Reliability ███░░░░░░░  12/15
  Uptime              ████░░░░░░   8/10
  Verification        ░░░░░░░░░░   0/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TOTAL: 73/100 — Good ✅
```

**Scoring features:**
- Bayesian smoothing prevents gaming with small sample sizes
- Timeout penalties (worse than failures)
- Review decay on old ratings
- Confidence levels (low/medium/high) based on data volume

## Architecture

```
agentdna/
├── src/
│   ├── registry/         # FastAPI server — register, search, heartbeat
│   ├── trust/            # Scoring engine + LLM-as-judge evaluator
│   ├── sandbox/          # 8-check verification suite
│   ├── marketplace/      # Task posting + escrow
│   ├── plugins/
│   │   ├── langchain.py  # LangChain wrapper
│   │   ├── crewai.py     # CrewAI wrapper
│   │   └── observe.py    # @observe decorator (works with anything)
│   ├── sdk/
│   │   ├── python/       # pip install agentdna-sdk
│   │   └── typescript/   # npm install @agentdna/sdk
│   └── dashboard/        # Web UI with Tailwind CSS
├── tests/                # pytest test suite
├── docs/
│   └── SPEC.md           # Full protocol specification
└── examples/
    └── agentdna.yaml     # Example agent card
```

## Agent Card (`agentdna.yaml`)

```yaml
agent:
  name: "TranscribePro"
  version: "2.1.0"
  description: "Audio transcription with speaker diarization"
  protocol: "a2a"
  endpoint: "https://transcribe-pro.example.com/a2a"

  capabilities:
    - skill: "transcribe"
      inputs: ["audio/wav", "audio/mp3"]
      output: "text/plain"
      languages: ["en", "zh", "es"]
      pricing:
        model: "per_minute"
        amount: 0.02
        currency: "USD"

  metadata:
    tags: ["transcription", "audio"]

  security:
    data_handling: "temporary"
    encryption: true
```

## Why AgentDNA?

| Without AgentDNA | With AgentDNA |
|-----------------|---------------|
| Hardcode which agents to call | Discover agents dynamically |
| Trust unknown agents blindly | Verified reputation scores |
| No pricing transparency | Compare agents by price & quality |
| Agents live in silos | Agents form an ecosystem |
| Manual integration | One SDK, any agent |

## Roadmap

- [x] Agent Card spec (`agentdna.yaml`)
- [x] Registry API (search, register, heartbeat)
- [x] Python & TypeScript SDKs
- [x] CLI tool
- [x] Trust scoring engine with Bayesian smoothing
- [x] Sandbox verification (8 checks)
- [x] Web dashboard with agent profiles
- [x] Framework plugins (LangChain, CrewAI, @observe)
- [ ] Task marketplace with escrow payments
- [ ] Heartbeat monitoring service
- [ ] LLM-as-judge quality evaluator integration
- [ ] Enterprise tier (private registries, SSO)

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

**Built on top of:**
- [A2A Protocol](https://a2a-protocol.org) — Agent-to-Agent communication (Google/Linux Foundation)
- [MCP](https://modelcontextprotocol.io) — Model Context Protocol (Anthropic)
- [AP2](https://developers.googleblog.com) — Agent Payments Protocol (Google)

**AgentDNA is to agents what DNS is to the internet.**
