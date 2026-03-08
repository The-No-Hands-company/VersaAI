/** VersaAI Desktop – API client (Tauri invoke wrapper). */

import { invoke } from "@tauri-apps/api/core";

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

// ---------------------------------------------------------------------------
// API functions (proxy through Tauri commands → FastAPI backend)
// ---------------------------------------------------------------------------

export async function chatSend(
  messages: ChatMessage[],
  model?: string,
  temperature?: number,
  maxTokens?: number,
): Promise<ChatResponse> {
  return invoke<ChatResponse>("chat_send", {
    messages,
    model: model ?? null,
    temperature: temperature ?? null,
    maxTokens: maxTokens ?? null,
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
