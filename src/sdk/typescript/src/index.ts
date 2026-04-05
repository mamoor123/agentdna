/**
 * 🧬 AgentDNA SDK — DNS for AI Agents
 *
 * Discovery, Trust & Marketplace for AI agents.
 */

// --- Types ---

export interface Pricing {
  model: "free" | "per_call" | "per_minute" | "per_token" | "per_item";
  amount: number;
  currency: string;
  freeTier?: number;
}

export interface Capability {
  skill: string;
  description?: string;
  inputs?: string[];
  output?: string;
  languages?: string[];
  pricing?: Pricing;
}

export interface TrustScore {
  total: number;
  taskCompletion: number;
  responseQuality: number;
  latencyReliability: number;
  uptimeScore: number;
  verificationBonus: number;
}

export interface Agent {
  id: string;
  name: string;
  version: string;
  description: string;
  protocol: "a2a" | "mcp" | "custom";
  endpoint: string;
  capabilities: Capability[];
  trustScore?: TrustScore;
  tags?: string[];
  verified?: boolean;
}

export interface SearchResult {
  agents: Agent[];
  total: number;
  query: Record<string, unknown>;
}

export interface TaskResult {
  taskId: string;
  agentId: string;
  status: "pending" | "in_progress" | "completed" | "failed" | "refunded";
  output?: string;
  cost?: number;
  currency?: string;
  durationSeconds?: number;
  error?: string;
}

// --- Client ---

const AGENTDNA_API_URL = process.env.AGENTDNA_API_URL || "https://api.agentdna.dev";

export class AgentDNAClient {
  private apiUrl: string;
  private apiKey: string;

  constructor(options?: { apiUrl?: string; apiKey?: string }) {
    this.apiUrl = (options?.apiUrl || AGENTDNA_API_URL).replace(/\/$/, "");
    this.apiKey = options?.apiKey || process.env.AGENTDNA_API_KEY || "";
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const resp = await fetch(`${this.apiUrl}${path}`, {
      method,
      headers: {
        Authorization: this.apiKey ? `Bearer ${this.apiKey}` : "",
        "Content-Type": "application/json",
        "User-Agent": "agentdna-typescript/0.1.0",
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!resp.ok) {
      throw new Error(`AgentDNA API error: ${resp.status} ${resp.statusText}`);
    }

    return resp.json() as T;
  }

  // --- Registry ---

  async register(agentCard: Record<string, unknown>): Promise<{ agentId: string }> {
    return this.request("POST", "/api/v1/agents", agentCard);
  }

  async getAgent(agentId: string): Promise<Agent> {
    return this.request("GET", `/api/v1/agents/${encodeURIComponent(agentId)}`);
  }

  // --- Discovery ---

  async search(params: {
    skill?: string;
    language?: string;
    maxPrice?: number;
    minReputation?: number;
    verified?: boolean;
    protocol?: string;
    limit?: number;
    offset?: number;
  }): Promise<SearchResult> {
    const query = new URLSearchParams();
    if (params.skill) query.set("skill", params.skill);
    if (params.language) query.set("language", params.language);
    if (params.maxPrice != null) query.set("max_price", String(params.maxPrice));
    if (params.minReputation != null) query.set("min_reputation", String(params.minReputation));
    if (params.verified != null) query.set("verified", String(params.verified));
    if (params.protocol) query.set("protocol", params.protocol);
    if (params.limit) query.set("limit", String(params.limit));
    if (params.offset) query.set("offset", String(params.offset));

    return this.request("GET", `/api/v1/agents/search?${query.toString()}`);
  }

  // --- Trust ---

  async getTrustScore(agentId: string): Promise<TrustScore> {
    return this.request("GET", `/api/v1/agents/${encodeURIComponent(agentId)}/trust`);
  }

  // --- Marketplace ---

  async createTask(agentId: string, task: Record<string, unknown>): Promise<{ taskId: string }> {
    return this.request("POST", `/api/v1/agents/${encodeURIComponent(agentId)}/tasks`, task);
  }

  async getTask(taskId: string): Promise<TaskResult> {
    return this.request("GET", `/api/v1/tasks/${encodeURIComponent(taskId)}`);
  }
}

// --- Convenience Functions ---

export async function findAgent(params: {
  skill?: string;
  language?: string;
  maxPrice?: number;
  minReputation?: number;
  verified?: boolean;
  apiKey?: string;
}): Promise<Agent | null> {
  const client = new AgentDNAClient({ apiKey: params.apiKey });
  const result = await client.search({ ...params, limit: 1 });
  return result.agents[0] || null;
}

export async function hireAgent(params: {
  agentId: string;
  task: string;
  inputFile?: string;
  inputUrl?: string;
  maxPrice?: number;
  timeout?: string;
  escrow?: boolean;
  apiKey?: string;
  pollIntervalMs?: number;
  maxWaitMs?: number;
}): Promise<TaskResult> {
  const client = new AgentDNAClient({ apiKey: params.apiKey });

  const taskPayload: Record<string, unknown> = {
    description: params.task,
    max_price: params.maxPrice,
    timeout: params.timeout || "5m",
    escrow: params.escrow ?? true,
  };

  if (params.inputFile) taskPayload.input = { type: "file", path: params.inputFile };
  else if (params.inputUrl) taskPayload.input = { type: "url", url: params.inputUrl };

  const { taskId } = await client.createTask(params.agentId, taskPayload);

  // Poll for completion with timeout
  const interval = params.pollIntervalMs || 2000;
  const maxWait = params.maxWaitMs || 600_000; // 10 minutes default
  let elapsed = 0;

  while (elapsed < maxWait) {
    const result = await client.getTask(taskId);
    if (["completed", "failed", "refunded"].includes(result.status)) {
      return result;
    }
    await new Promise((r) => setTimeout(r, interval));
    elapsed += interval;
  }

  // Timed out
  return {
    taskId,
    agentId: params.agentId,
    status: "failed",
    error: `Timed out after ${maxWait}ms waiting for task completion`,
  };
}
