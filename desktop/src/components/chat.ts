/** Chat view — send messages to LLM via VersaAI backend with real-time streaming. */

import {
  chatSendStream,
  getSettings,
  listConversations,
  getConversationMessages,
  deleteConversation,
  type ChatMessage,
  type ConversationSummary,
  type SettingsView,
} from "../api";

let messages: ChatMessage[] = [];
let loading = false;
let containerEl: HTMLElement | null = null;
let conversationId: string = crypto.randomUUID();
let abortController: AbortController | null = null;
let conversations: ConversationSummary[] = [];
let runtimeSettings: SettingsView | null = null;

export function renderChat(el: HTMLElement) {
  containerEl = el;
  el.innerHTML = `
    <div class="chat-container">
      <div class="chat-history-panel" id="chat-history">
        <div class="chat-history-panel__header">
          <span>Conversations</span>
          <button class="btn btn--primary" id="new-chat-btn" style="font-size:11px;padding:2px 8px;">+ New</button>
        </div>
        <div id="conv-list"></div>
      </div>
      <div class="chat-messages" id="chat-messages"></div>
      <div class="chat-input-wrapper">
        <textarea
          id="chat-input"
          class="chat-input"
          placeholder="Message VersaAI…"
          rows="1"
        ></textarea>
        <button id="chat-send" class="btn btn--primary">Send</button>
        <button id="chat-stop" class="btn btn--danger" style="display:none">Stop</button>
      </div>
    </div>
  `;

  const input = el.querySelector<HTMLTextAreaElement>("#chat-input")!;
  const sendBtn = el.querySelector<HTMLButtonElement>("#chat-send")!;
  const stopBtn = el.querySelector<HTMLButtonElement>("#chat-stop")!;
  const newChatBtn = el.querySelector<HTMLButtonElement>("#new-chat-btn")!;

  sendBtn.addEventListener("click", () => handleSend(input));
  stopBtn.addEventListener("click", () => handleStop());
  newChatBtn.addEventListener("click", () => startNewChat());

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(input);
    }
  });

  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 200)}px`;
  });

  renderMessages();
  loadConversations();
  loadSettings();
}

async function loadSettings() {
  try {
    runtimeSettings = await getSettings();
  } catch {
    // Non-fatal — will use backend defaults
  }
}

async function loadConversations() {
  try {
    conversations = await listConversations(30);
  } catch {
    conversations = [];
  }
  renderConvList();
}

function renderConvList() {
  const list = containerEl?.querySelector("#conv-list");
  if (!list) return;

  if (conversations.length === 0) {
    list.innerHTML = '<span style="font-size:11px;color:var(--text-muted);padding:4px 8px;">No history yet</span>';
    return;
  }

  list.innerHTML = conversations
    .map((c) => {
      const active = c.id === conversationId ? " conv-item--active" : "";
      const label = c.title || `Chat ${c.id.slice(0, 8)}…`;
      return `
        <div class="conv-item${active}" data-conv-id="${escapeHtml(c.id)}">
          <span>${escapeHtml(label)}</span>
          <button class="conv-item__del" data-del-id="${escapeHtml(c.id)}" title="Delete">✕</button>
        </div>`;
    })
    .join("");

  list.querySelectorAll(".conv-item").forEach((el) => {
    el.addEventListener("click", (e) => {
      // Don't load if clicking the delete button
      if ((e.target as HTMLElement).classList.contains("conv-item__del")) return;
      const id = (el as HTMLElement).dataset.convId!;
      switchConversation(id);
    });
  });

  list.querySelectorAll(".conv-item__del").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = (btn as HTMLElement).dataset.delId!;
      try {
        await deleteConversation(id);
        if (id === conversationId) startNewChat();
        await loadConversations();
      } catch { /* ignore */ }
    });
  });
}

async function switchConversation(id: string) {
  conversationId = id;
  messages = [];
  renderMessages();
  renderConvList();

  try {
    const msgs = await getConversationMessages(id);
    messages = msgs.map((m) => ({ role: m.role as ChatMessage["role"], content: m.content }));
    renderMessages();
  } catch {
    // Conversation may have no messages yet
  }
}

function startNewChat() {
  conversationId = crypto.randomUUID();
  messages = [];
  renderMessages();
  renderConvList();
}

function handleStop() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
}

async function handleSend(input: HTMLTextAreaElement) {
  const text = input.value.trim();
  if (!text || loading) return;

  messages.push({ role: "user", content: text });
  input.value = "";
  input.style.height = "auto";
  loading = true;

  // Add empty assistant message that will be filled by streaming
  const assistantIdx = messages.length;
  messages.push({ role: "assistant", content: "" });

  renderMessages();
  updateButtons();

  abortController = new AbortController();

  try {
    await chatSendStream(
      messages.slice(0, assistantIdx),  // Send only up to (not including) the empty assistant msg
      (chunk: string) => {
        messages[assistantIdx].content += chunk;
        updateStreamingMessage(assistantIdx);
      },
      {
        conversationId,
        model: runtimeSettings?.default_model,
        temperature: runtimeSettings?.temperature,
        maxTokens: runtimeSettings?.max_tokens,
        signal: abortController.signal,
      },
    );
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      // User cancelled — keep partial content
      if (!messages[assistantIdx].content) {
        messages[assistantIdx].content = "⏹ Generation stopped.";
      }
    } else {
      messages[assistantIdx].content =
        `⚠ Error: ${err instanceof Error ? err.message : String(err)}`;
    }
  } finally {
    loading = false;
    abortController = null;
    renderMessages();
    updateButtons();
    loadConversations();
  }
}

function updateStreamingMessage(idx: number) {
  const msgEl = containerEl?.querySelector(`[data-msg-idx="${idx}"] .message__body`);
  if (msgEl) {
    msgEl.textContent = messages[idx].content;
    // Scroll to bottom
    const messagesEl = containerEl?.querySelector("#chat-messages");
    if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
  }
}

function renderMessages() {
  const messagesEl = containerEl?.querySelector("#chat-messages");
  if (!messagesEl) return;

  messagesEl.innerHTML = messages
    .map(
      (m, i) => `
    <div class="message message--${m.role}" data-msg-idx="${i}">
      <div class="message__avatar">${m.role === "user" ? "U" : "AI"}</div>
      <div class="message__body">${escapeHtml(m.content)}${
        loading && m.role === "assistant" && i === messages.length - 1 && !m.content
          ? '<span class="spinner"></span> Thinking…'
          : ""
      }</div>
    </div>
  `,
    )
    .join("");

  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function updateButtons() {
  const sendBtn = containerEl?.querySelector<HTMLButtonElement>("#chat-send");
  const stopBtn = containerEl?.querySelector<HTMLButtonElement>("#chat-stop");
  if (sendBtn) sendBtn.style.display = loading ? "none" : "";
  if (stopBtn) stopBtn.style.display = loading ? "" : "none";
}

function escapeHtml(str: string): string {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
