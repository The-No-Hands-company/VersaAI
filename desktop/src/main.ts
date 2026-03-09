/** VersaAI Desktop – Application entry point. */

import { healthCheck } from "./api";
import { renderSidebar, setActiveView } from "./components/sidebar";
import { renderChat } from "./components/chat";
import { renderAgents } from "./components/agents";
import { renderRag } from "./components/rag";
import { renderSettings } from "./components/settings";

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", async () => {
  const app = document.getElementById("app");
  if (!app) return;

  app.innerHTML = `
    <aside id="sidebar" class="sidebar"></aside>
    <main id="content" class="content"></main>
    <div id="status-bar" class="status-bar">
      <span id="status-indicator" class="indicator offline"></span>
      <span id="status-text">Connecting…</span>
    </div>
  `;

  renderSidebar(document.getElementById("sidebar")!);

  // Default view
  navigateTo("chat");

  // Check backend health
  checkBackend();
});

// ---------------------------------------------------------------------------
// Routing
// ---------------------------------------------------------------------------

type View = "chat" | "agents" | "rag" | "settings";

const renderers: Record<View, (el: HTMLElement) => void> = {
  chat: renderChat,
  agents: renderAgents,
  rag: renderRag,
  settings: renderSettings,
};

export function navigateTo(view: View) {
  const content = document.getElementById("content");
  if (!content) return;
  content.innerHTML = "";
  setActiveView(view);
  renderers[view](content);
}

// ---------------------------------------------------------------------------
// Health polling
// ---------------------------------------------------------------------------

async function checkBackend() {
  const indicator = document.getElementById("status-indicator");
  const text = document.getElementById("status-text");

  try {
    const h = await healthCheck();
    indicator?.classList.remove("offline");
    indicator?.classList.add("online");
    if (text) text.textContent = `Backend: ${h.status ?? "ok"}`;
  } catch {
    indicator?.classList.remove("online");
    indicator?.classList.add("offline");
    if (text) text.textContent = "Backend offline";
  }

  // Re-check every 30 s
  setTimeout(checkBackend, 30_000);
}

// Expose for sidebar
(window as unknown as Record<string, unknown>).__navigateTo = navigateTo;
