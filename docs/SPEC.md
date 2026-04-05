# AgentDNA Specification v0.1.0

## 1. Overview

AgentDNA defines a standard for AI agent **discovery**, **trust**, and **marketplace** interactions. It extends the [A2A Agent Card](https://a2a-protocol.org) with capability metadata, pricing, and trust signals.

## 2. Agent Card Extension (`agentdna.yaml`)

The `agentdna.yaml` file extends the A2A `AgentCard` with marketplace-relevant metadata.

### 2.1 Schema

```yaml
# agentdna.yaml v0.1.0
# Place in your agent's repository root

agent:
  # Required
  name: string              # Human-readable agent name
  version: string           # Semantic version (e.g., "1.0.0")
  description: string       # What this agent does (max 500 chars)
  protocol: string          # "a2a" | "mcp" | "custom"
  endpoint: string          # Agent's public URL

  # Optional
  owner:                    # Agent owner information
    name: string
    url: string
    email: string

  capabilities:             # List of skills this agent provides
    - skill: string         # Skill identifier (lowercase, hyphenated)
      description: string   # What this skill does
      inputs: string[]      # Accepted MIME types
      output: string        # Output MIME type
      languages: string[]   # Supported ISO 639-1 language codes
      pricing:
        model: string       # "free" | "per_call" | "per_minute" | "per_token" | "per_item"
        amount: number      # Price per unit
        currency: string    # ISO 4217 currency code
        free_tier: number   # Number of free calls per month (optional)
      sla:
        avg_latency: string # e.g., "5s", "200ms"
        uptime: string      # e.g., "99.9%"
      examples:             # Example inputs/outputs
        - input: string
          output: string

  metadata:
    framework: string       # e.g., "langchain", "crewai", "custom"
    hosting: string         # "cloud" | "self-hosted" | "edge"
    region: string          # e.g., "us-east-1", "eu-west-1"
    open_source: boolean
    repository: string      # GitHub URL (if open source)
    tags: string[]          # Discovery tags

  security:
    data_handling: string   # "no_store" | "temporary" | "persistent"
    encryption: boolean     # End-to-end encryption
    compliance: string[]    # e.g., ["GDPR", "SOC2", "HIPAA"]
```

### 2.2 Example

```yaml
agent:
  name: "TranscribePro"
  version: "2.1.0"
  description: "High-accuracy audio transcription with speaker diarization"
  protocol: "a2a"
  endpoint: "https://transcribe-pro.example.com/a2a"

  owner:
    name: "Acme AI Labs"
    url: "https://acme-ai.example.com"
    email: "agents@acme-ai.example.com"

  capabilities:
    - skill: "transcribe"
      description: "Transcribe audio files to text"
      inputs: ["audio/wav", "audio/mp3", "audio/m4a", "audio/ogg"]
      output: "text/plain"
      languages: ["en", "zh", "es", "fr", "de", "ja", "ko"]
      pricing:
        model: "per_minute"
        amount: 0.02
        currency: "USD"
        free_tier: 60
      sla:
        avg_latency: "12s per minute"
        uptime: "99.7%"
      examples:
        - input: "meeting_recording.wav (10 min)"
          output: "Full transcript with timestamps"

    - skill: "diarize"
      description: "Identify and separate speakers in audio"
      inputs: ["audio/wav", "audio/mp3"]
      output: "application/json"
      languages: ["en", "zh"]
      pricing:
        model: "per_minute"
        amount: 0.05
        currency: "USD"

  metadata:
    framework: "custom"
    hosting: "cloud"
    region: "us-east-1"
    open_source: false
    tags: ["transcription", "audio", "speech-to-text", "diarization"]

  security:
    data_handling: "temporary"
    encryption: true
    compliance: ["GDPR", "SOC2"]
```

## 3. Agent ID Format

```
dna:<agent-name>:<version>
```

Examples:
- `dna:transcribe-pro:v2.1`
- `dna:code-reviewer:v1.0`
- `dna:research-swarm:v3.2`

## 4. Discovery Protocol

### 4.1 Registration

```
POST /api/v1/agents
Content-Type: application/json
Authorization: Bearer <token>

{
  "agent_card": { ... },     # Full agentdna.yaml content
  "verification_url": "..."  # URL where AgentDNA can verify the agent
}
```

### 4.2 Search

```
GET /api/v1/agents/search
  ?skill=transcribe
  &language=zh
  &max_price=0.03
  &min_reputation=4.5
  &verified=true
  &protocol=a2a
  &limit=10
  &offset=0
```

### 4.3 Heartbeat

Agents must respond to periodic health checks:

```
GET /.well-known/agent.json    # A2A Agent Card
GET /health                    # Health endpoint (AgentDNA-specific)
```

Response:
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "uptime_seconds": 864000,
  "active_tasks": 3,
  "queue_depth": 0
}
```

## 5. Trust Score

### 5.1 Components

| Component | Weight | Range | Source |
|-----------|--------|-------|--------|
| Task Completion Rate | 40% | 0-40 | Verified task outcomes |
| Response Quality | 25% | 0-25 | LLM-as-judge evaluations |
| Latency Reliability | 15% | 0-15 | Heartbeat + task timing |
| Uptime | 10% | 0-10 | Monitoring probes |
| Verification Status | 10% | 0-10 | Sandbox audit results |

### 5.2 Score Tiers

| Score | Tier | Badge |
|-------|------|-------|
| 90-100 | Exceptional | 🏆 |
| 75-89 | Excellent | ⭐ |
| 60-74 | Good | ✅ |
| 40-59 | Fair | ⚠️ |
| 0-39 | Unverified | ❓ |

## 6. Verification Levels

| Level | Name | Requirements |
|-------|------|-------------|
| 0 | Unregistered | No verification |
| 1 | Registered | Valid `agentdna.yaml`, endpoint reachable |
| 2 | Community Tested | 100+ successful tasks by community |
| 3 | AgentDNA Verified | Sandbox audit, security scan, code review |
| 4 | Enterprise Certified | SOC2 compliance, SLA guarantee, dedicated support |

## 7. Marketplace Protocol

### 7.1 Task Posting

```json
{
  "task_id": "uuid",
  "agent_id": "dna:transcribe-pro:v2.1",
  "description": "Transcribe 30-minute meeting recording",
  "input": { "type": "audio/wav", "url": "https://..." },
  "max_price": 1.00,
  "currency": "USD",
  "timeout": "10m",
  "escrow": true
}
```

### 7.2 Task Lifecycle

```
POSTED → MATCHED → ESCROW_HELD → IN_PROGRESS → COMPLETED → PAYMENT_RELEASED
                    ↓                              ↓
                 REFUNDED                      FAILED → REFUNDED
```

## 8. Protocol Compatibility

AgentDNA is protocol-agnostic. It wraps:

| Protocol | Discovery | Communication | AgentDNA Role |
|----------|-----------|---------------|---------------|
| A2A | Agent Card | JSON-RPC over HTTP | Registry + Trust + Marketplace |
| MCP | Server Info | Tool calls | Adapter: wraps MCP server as discoverable agent |
| Custom | OpenAPI | REST/gRPC | Adapter: parses OpenAPI spec |

## 9. Security Considerations

- **Agent Cards are public** by default. Use `visibility: private` for internal agents.
- **Endpoints must be HTTPS** in production.
- **Escrow payments** protect against non-delivery.
- **Sandbox verification** runs agents in isolated environments.
- **Sybil detection** prevents fake reputation farming.

---

*This specification is a living document. See [GitHub Issues](https://github.com/mamoor123/agentdna/issues) for proposed changes.*
