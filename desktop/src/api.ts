/** VersaAI Desktop – API client (Tauri invoke wrapper + direct fetch for SSE). */

import { invoke } from "@tauri-apps/api/core";

const API_BASE = "http://127.0.0.1:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatChoice {
  index: number;
  message: ChatMessage;
}

export interface ChatResponse {
  id: string;
  choices: ChatChoice[];
}

export interface AgentInfo {
  name: string;
  description: string;
  version: string;
  capabilities: string[];
  status: string;
}

export interface HealthStatus {
  status: string;
  [key: string]: unknown;
}

export interface SettingsView {
  default_provider: string;
  default_model: string;
  temperature: number;
  max_tokens: number;
  providers: Record<string, { enabled: boolean; base_url?: string; default_model?: string }>;
  rag_enabled: boolean;
  rag_top_k: number;
}

export interface ModelInfo {
  name: string;
  provider: string;
  size?: string;
  quantization?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: number;
}

// ---------------------------------------------------------------------------
// Non-streaming API (via Tauri commands)
// ---------------------------------------------------------------------------

export async function chatSend(
  messages: ChatMessage[],
  model?: string,
  temperature?: number,
  maxTokens?: number,
  conversationId?: string,
): Promise<ChatResponse> {
  return invoke<ChatResponse>("chat_send", {
    messages,
    model: model ?? null,
    temperature: temperature ?? null,
    maxTokens: maxTokens ?? null,
    conversationId: conversationId ?? null,
  });
}

export async function agentList(): Promise<AgentInfo[]> {
  return invoke<AgentInfo[]>("agent_list");
}

export async function agentExecute(
  agent: string,
  task: string,
): Promise<Record<string, unknown>> {
  return invoke<Record<string, unknown>>("agent_execute", { agent, task });
}

export async function ragIngest(
  text: string,
  metadata?: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return invoke<Record<string, unknown>>("rag_ingest", {
    text,
    metadata: metadata ?? null,
  });
}

export async function ragQuery(
  question: string,
  topK?: number,
): Promise<Record<string, unknown>> {
  return invoke<Record<string, unknown>>("rag_query", {
    question,
    topK: topK ?? null,
  });
}

export async function healthCheck(): Promise<HealthStatus> {
  return invoke<HealthStatus>("health_check");
}

// ---------------------------------------------------------------------------
// Settings API (direct fetch — no Tauri command needed)
// ---------------------------------------------------------------------------

export async function getSettings(): Promise<SettingsView> {
  const resp = await fetch(`${API_BASE}/v1/settings`);
  if (!resp.ok) throw new Error(`Settings fetch failed: ${resp.status}`);
  return resp.json();
}

export async function updateSettings(
  update: Partial<Pick<SettingsView, "default_provider" | "default_model" | "temperature" | "max_tokens" | "rag_enabled" | "rag_top_k">>,
): Promise<SettingsView> {
  const resp = await fetch(`${API_BASE}/v1/settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err?.error?.message ?? `Update failed: ${resp.status}`);
  }
  return resp.json();
}

export async function listModels(): Promise<ModelInfo[]> {
  const resp = await fetch(`${API_BASE}/v1/settings/models`);
  if (!resp.ok) throw new Error(`Models list failed: ${resp.status}`);
  const data = await resp.json();
  return data.models ?? [];
}

// ---------------------------------------------------------------------------
// Conversation memory (direct fetch)
// ---------------------------------------------------------------------------

export async function listConversations(limit = 50): Promise<ConversationSummary[]> {
  const resp = await fetch(`${API_BASE}/v1/memory/conversations?limit=${limit}`);
  if (!resp.ok) throw new Error(`List conversations failed: ${resp.status}`);
  return resp.json();
}

export async function getConversationMessages(convId: string): Promise<ConversationMessage[]> {
  const resp = await fetch(`${API_BASE}/v1/memory/conversations/${encodeURIComponent(convId)}/messages`);
  if (!resp.ok) throw new Error(`Get messages failed: ${resp.status}`);
  const data = await resp.json();
  return data.messages ?? data;
}

export async function deleteConversation(convId: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/v1/memory/conversations/${encodeURIComponent(convId)}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`Delete conversation failed: ${resp.status}`);
}

// ---------------------------------------------------------------------------
// RAG stats & documents (direct fetch)
// ---------------------------------------------------------------------------

export interface RagStats {
  total_chunks: number;
  total_documents: number;
  total_queries: number;
  [key: string]: unknown;
}

export interface RagDocument {
  id: string;
  content?: string;
  metadata?: Record<string, unknown>;
}

export async function ragStats(): Promise<RagStats> {
  const resp = await fetch(`${API_BASE}/v1/rag/stats`);
  if (!resp.ok) throw new Error(`RAG stats failed: ${resp.status}`);
  return resp.json();
}

export async function ragDocuments(limit = 100, offset = 0): Promise<{ documents: RagDocument[]; total: number }> {
  const resp = await fetch(`${API_BASE}/v1/rag/documents?limit=${limit}&offset=${offset}`);
  if (!resp.ok) throw new Error(`RAG documents failed: ${resp.status}`);
  return resp.json();
}

// ---------------------------------------------------------------------------
// Streaming chat (direct fetch for SSE — bypasses Tauri invoke)
// ---------------------------------------------------------------------------

/**
 * Send a streaming chat request. Calls `onChunk` for each content token,
 * and returns the full assembled content when complete.
 */
export async function chatSendStream(
  messages: ChatMessage[],
  onChunk: (content: string) => void,
  opts?: {
    model?: string;
    temperature?: number;
    maxTokens?: number;
    conversationId?: string;
    signal?: AbortSignal;
  },
): Promise<string> {
  const body = {
    model: opts?.model ?? null,
    messages,
    temperature: opts?.temperature ?? null,
    max_tokens: opts?.maxTokens ?? null,
    stream: true,
    conversation_id: opts?.conversationId ?? null,
  };

  const resp = await fetch(`${API_BASE}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: opts?.signal,
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err?.error?.message ?? `Chat error: ${resp.status}`);
  }

  const reader = resp.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";
  let fullContent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE lines
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (payload === "[DONE]") break;

      try {
        const chunk = JSON.parse(payload);
        const delta = chunk?.choices?.[0]?.delta;
        if (delta?.content) {
          fullContent += delta.content;
          onChunk(delta.content);
        }
      } catch {
        // Skip malformed chunks
      }
    }
  }

  return fullContent;
}

// ---------------------------------------------------------------------------
// Streaming agent execution (direct fetch for SSE)
// ---------------------------------------------------------------------------

export interface AgentStreamEvent {
  type: "step" | "result" | "error";
  data: Record<string, unknown>;
}

/**
 * Execute an agent with SSE streaming. Calls `onEvent` for each step/result.
 */
export async function agentExecuteStream(
  agent: string,
  task: string,
  onEvent: (event: AgentStreamEvent) => void,
  opts?: {
    model?: string;
    config?: Record<string, unknown>;
    timeout?: number;
    signal?: AbortSignal;
  },
): Promise<void> {
  const body = {
    agent,
    task,
    model: opts?.model ?? null,
    config: opts?.config ?? null,
    stream: true,
    timeout: opts?.timeout ?? 300,
  };

  const resp = await fetch(`${API_BASE}/v1/agents/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: opts?.signal,
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err?.error?.message ?? `Agent error: ${resp.status}`);
  }

  const reader = resp.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      if (!part.trim()) continue;

      // Parse SSE "event: xxx\ndata: {...}"
      let eventType = "step";
      let dataStr = "";

      for (const line of part.split("\n")) {
        if (line.startsWith("event: ")) eventType = line.slice(7).trim();
        else if (line.startsWith("data: ")) dataStr = line.slice(6).trim();
      }

      if (dataStr === "[DONE]") return;
      if (!dataStr) continue;

      try {
        const data = JSON.parse(dataStr);
        onEvent({ type: eventType as AgentStreamEvent["type"], data });
      } catch {
        // Skip malformed events
      }
    }
  }
}
