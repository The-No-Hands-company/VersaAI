/** Chat view — send messages to LLM via VersaAI backend with real-time streaming. */

import { chatSendStream, type ChatMessage } from "../api";

let messages: ChatMessage[] = [];
let loading = false;
let containerEl: HTMLElement | null = null;
let conversationId: string = crypto.randomUUID();
let abortController: AbortController | null = null;

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
        <button id="chat-stop" class="btn btn--danger" style="display:none">Stop</button>
      </div>
    </div>
  `;

  const input = el.querySelector<HTMLTextAreaElement>("#chat-input")!;
  const sendBtn = el.querySelector<HTMLButtonElement>("#chat-send")!;
  const stopBtn = el.querySelector<HTMLButtonElement>("#chat-stop")!;

  sendBtn.addEventListener("click", () => handleSend(input));
  stopBtn.addEventListener("click", () => handleStop());

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
