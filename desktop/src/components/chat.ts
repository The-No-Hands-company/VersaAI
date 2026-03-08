/** Chat view — send messages to LLM via VersaAI backend. */

import { chatSend, type ChatMessage } from "../api";

let messages: ChatMessage[] = [];
let loading = false;
let containerEl: HTMLElement | null = null;
let conversationId: string = crypto.randomUUID();

export function renderChat(el: HTMLElement) {
  containerEl = el;
  el.innerHTML = `
    <div class="chat-container">
      <div class="chat-messages" id="chat-messages"></div>
      <div class="chat-input-wrapper">
        <textarea
          id="chat-input"
          class="chat-input"
          placeholder="Message VersaAI…"
          rows="1"
        ></textarea>
        <button id="chat-send" class="btn btn--primary">Send</button>
      </div>
    </div>
  `;

  const input = el.querySelector<HTMLTextAreaElement>("#chat-input")!;
  const sendBtn = el.querySelector<HTMLButtonElement>("#chat-send")!;

  sendBtn.addEventListener("click", () => handleSend(input));

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(input);
    }
  });

  // Auto-resize textarea
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 200)}px`;
  });

  renderMessages();
}

async function handleSend(input: HTMLTextAreaElement) {
  const text = input.value.trim();
  if (!text || loading) return;

  messages.push({ role: "user", content: text });
  input.value = "";
  input.style.height = "auto";
  loading = true;

  renderMessages();
  updateSendButton();

  try {
    const resp = await chatSend(messages, undefined, undefined, undefined, conversationId);
    const reply = resp.choices?.[0]?.message;
    if (reply) {
      messages.push(reply);
    }
  } catch (err) {
    messages.push({
      role: "assistant",
      content: `⚠ Error: ${err instanceof Error ? err.message : String(err)}`,
    });
  } finally {
    loading = false;
    renderMessages();
    updateSendButton();
  }
}

function renderMessages() {
  const messagesEl = containerEl?.querySelector("#chat-messages");
  if (!messagesEl) return;

  messagesEl.innerHTML = messages
    .map(
      (m) => `
    <div class="message message--${m.role}">
      <div class="message__avatar">${m.role === "user" ? "U" : "AI"}</div>
      <div class="message__body">${escapeHtml(m.content)}</div>
    </div>
  `,
    )
    .join("");

  if (loading) {
    messagesEl.innerHTML += `
      <div class="message message--assistant">
        <div class="message__avatar">AI</div>
        <div class="message__body"><span class="spinner"></span> Thinking…</div>
      </div>
    `;
  }

  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function updateSendButton() {
  const btn = containerEl?.querySelector<HTMLButtonElement>("#chat-send");
  if (btn) btn.disabled = loading;
}

function escapeHtml(str: string): string {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
