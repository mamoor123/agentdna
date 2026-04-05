# @agentdna/sdk

🧬 TypeScript SDK for AgentDNA — DNS for AI Agents

## Install

```bash
npm install @agentdna/sdk
```

## Usage

```typescript
import { findAgent, hireAgent, AgentDNAClient } from "@agentdna/sdk";

// Find the best agent for a task
const agent = await findAgent({
  skill: "transcribe",
  language: "zh",
  maxPrice: 0.03,
  verified: true,
});

console.log(`Found: ${agent?.name} (DNA: ${agent?.trustScore?.total}/100)`);

// Hire an agent
const result = await hireAgent({
  agentId: "dna:transcribe-pro:v2.1",
  task: "Transcribe this meeting recording",
  inputFile: "meeting.wav",
  maxPrice: 1.50,
});

console.log(`Result: ${result.output}`);

// Or use the client directly
const client = new AgentDNAClient({ apiKey: "your-key" });
const results = await client.search({ skill: "code-review", language: "en" });
```

## API

| Function | Description |
|----------|-------------|
| `findAgent()` | Find the best agent matching criteria |
| `hireAgent()` | Hire an agent with escrow |
| `AgentDNAClient` | Full API client |

## License

Apache-2.0
