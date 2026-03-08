use serde::{Deserialize, Serialize};

/// Base URL for the VersaAI FastAPI backend.
const API_BASE: &str = "http://127.0.0.1:8000";

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatRequest {
    pub model: Option<String>,
    pub messages: Vec<ChatMessage>,
    pub temperature: Option<f64>,
    pub max_tokens: Option<u32>,
    pub stream: Option<bool>,
    pub conversation_id: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatChoice {
    pub index: u32,
    pub message: ChatMessage,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatResponse {
    pub id: String,
    pub choices: Vec<ChatChoice>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AgentInfo {
    pub name: String,
    pub description: String,
    pub version: String,
    pub capabilities: Vec<String>,
    pub status: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AgentExecRequest {
    pub agent: String,
    pub task: String,
    pub timeout: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RagIngestRequest {
    pub text: String,
    pub metadata: Option<serde_json::Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RagQueryRequest {
    pub question: String,
    pub top_k: Option<u32>,
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

fn client() -> reqwest::Client {
    reqwest::Client::new()
}

// ---------------------------------------------------------------------------
// Tauri commands
// ---------------------------------------------------------------------------

/// Send a chat message to the VersaAI API and return the assistant reply.
#[tauri::command]
pub async fn chat_send(
    messages: Vec<ChatMessage>,
    model: Option<String>,
    temperature: Option<f64>,
    max_tokens: Option<u32>,
    conversation_id: Option<String>,
) -> Result<ChatResponse, String> {
    let body = ChatRequest {
        model,
        messages,
        temperature,
        max_tokens,
        stream: Some(false),
        conversation_id,
    };

    let resp = client()
        .post(format!("{API_BASE}/v1/chat/completions"))
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("Network error: {e}"))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let text = resp.text().await.unwrap_or_default();
        return Err(format!("API error {status}: {text}"));
    }

    resp.json::<ChatResponse>()
        .await
        .map_err(|e| format!("Parse error: {e}"))
}

/// List registered agents.
#[tauri::command]
pub async fn agent_list() -> Result<Vec<AgentInfo>, String> {
    let resp = client()
        .get(format!("{API_BASE}/v1/agents"))
        .send()
        .await
        .map_err(|e| format!("Network error: {e}"))?;

    if !resp.status().is_success() {
        let text = resp.text().await.unwrap_or_default();
        return Err(format!("API error: {text}"));
    }

    // The API returns {"agents": [...]}
    let body: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Parse error: {e}"))?;

    let agents = body
        .get("agents")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    serde_json::from_value(serde_json::Value::Array(agents))
        .map_err(|e| format!("Deserialize error: {e}"))
}

/// Execute an agent task.
#[tauri::command]
pub async fn agent_execute(agent: String, task: String) -> Result<serde_json::Value, String> {
    let body = AgentExecRequest { agent, task, timeout: Some(300.0) };

    let resp = client()
        .post(format!("{API_BASE}/v1/agents/execute"))
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("Network error: {e}"))?;

    if !resp.status().is_success() {
        let text = resp.text().await.unwrap_or_default();
        return Err(format!("API error: {text}"));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Parse error: {e}"))
}

/// Ingest text into the RAG system.
#[tauri::command]
pub async fn rag_ingest(text: String, metadata: Option<serde_json::Value>) -> Result<serde_json::Value, String> {
    let body = RagIngestRequest { text, metadata };

    let resp = client()
        .post(format!("{API_BASE}/v1/rag/ingest"))
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("Network error: {e}"))?;

    if !resp.status().is_success() {
        let text = resp.text().await.unwrap_or_default();
        return Err(format!("API error: {text}"));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Parse error: {e}"))
}

/// Query the RAG system.
#[tauri::command]
pub async fn rag_query(question: String, top_k: Option<u32>) -> Result<serde_json::Value, String> {
    let body = RagQueryRequest { question, top_k };

    let resp = client()
        .post(format!("{API_BASE}/v1/rag/query"))
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("Network error: {e}"))?;

    if !resp.status().is_success() {
        let text = resp.text().await.unwrap_or_default();
        return Err(format!("API error: {text}"));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Parse error: {e}"))
}

/// Health check — verify the API is reachable.
#[tauri::command]
pub async fn health_check() -> Result<serde_json::Value, String> {
    let resp = client()
        .get(format!("{API_BASE}/v1/health"))
        .send()
        .await
        .map_err(|e| format!("Backend unreachable: {e}"))?;

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Parse error: {e}"))
}
