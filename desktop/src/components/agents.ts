/** Agents view — list and execute agents with real-time streaming progress. */

import {
  agentList,
  agentExecuteStream,
  getSettings,
  type AgentInfo,
  type AgentStreamEvent,
  type SettingsView,
} from "../api";

let agents: AgentInfo[] = [];
let loadError: string | null = null;
let containerEl: HTMLElement | null = null;
const runningAborts = new Map<string, AbortController>();
let runtimeSettings: SettingsView | null = null;

export function renderAgents(el: HTMLElement) {
  containerEl = el;
  el.innerHTML = `
    <h1 class="heading">Agents</h1>
    <div id="agents-grid" class="agents-grid">
      <p style="color: var(--text-muted)">Loading agents…</p>
    </div>
  `;

  loadAgents();
  getSettings().then((s) => { runtimeSettings = s; }).catch(() => {});
}

async function loadAgents() {
  try {
    agents = await agentList();
    loadError = null;
  } catch (err) {
    loadError = err instanceof Error ? err.message : String(err);
  }
  renderGrid();
}

function renderGrid() {
  const grid = containerEl?.querySelector("#agents-grid");
  if (!grid) return;

  if (loadError) {
    grid.innerHTML = `<p style="color: var(--error)">Failed to load agents: ${escapeHtml(loadError)}</p>`;
    return;
  }

  if (agents.length === 0) {
    grid.innerHTML = `<p style="color: var(--text-muted)">No agents registered.</p>`;
    return;
  }

  grid.innerHTML = agents
    .map(
      (a, i) => `
    <div class="agent-card" data-idx="${i}">
      <div class="agent-card__header">
        <span class="agent-card__name">${escapeHtml(a.name)}</span>
        <span class="agent-card__status agent-card__status--active">${escapeHtml(a.status)}</span>
      </div>
      <p class="agent-card__desc">${escapeHtml(a.description)}</p>
      <div class="agent-card__caps">
        ${a.capabilities.map((c) => `<span class="agent-card__cap">${escapeHtml(c)}</span>`).join("")}
      </div>
      <div class="agent-card__actions">
        <input class="agent-task-input" placeholder="Enter task…" data-agent="${escapeHtml(a.name)}" />
        <button class="btn btn--primary btn--exec" data-agent="${escapeHtml(a.name)}">Execute</button>
        <button class="btn btn--danger btn--cancel" data-agent="${escapeHtml(a.name)}" style="display:none">Cancel</button>
      </div>
      <div class="agent-steps" id="agent-steps-${i}" style="display:none; margin-top:8px;"></div>
      <div class="agent-result" id="agent-result-${i}" style="display:none; margin-top:8px; font-size:13px; color:var(--text-secondary); white-space:pre-wrap;"></div>
    </div>
  `,
    )
    .join("");

  // Bind execute buttons
  grid.querySelectorAll(".btn--exec").forEach((btn) => {
    btn.addEventListener("click", (e) => handleExecute(e));
  });

  // Bind cancel buttons
  grid.querySelectorAll(".btn--cancel").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const agentName = (e.currentTarget as HTMLElement).dataset.agent!;
      const controller = runningAborts.get(agentName);
      if (controller) controller.abort();
    });
  });
}

async function handleExecute(e: Event) {
  const execBtn = e.currentTarget as HTMLButtonElement;
  const agentName = execBtn.dataset.agent!;
  const card = execBtn.closest(".agent-card")!;
  const input = card.querySelector<HTMLInputElement>(".agent-task-input")!;
  const stepsDiv = card.querySelector<HTMLElement>(".agent-steps")!;
  const resultDiv = card.querySelector<HTMLElement>(".agent-result")!;
  const cancelBtn = card.querySelector<HTMLButtonElement>(".btn--cancel")!;
  const task = input.value.trim();
  if (!task) return;

  // UI state: running
  execBtn.disabled = true;
  execBtn.style.display = "none";
  cancelBtn.style.display = "";
  stepsDiv.style.display = "block";
  stepsDiv.innerHTML = '<span class="spinner"></span> Starting…';
  resultDiv.style.display = "none";
  resultDiv.style.color = "";

  const abort = new AbortController();
  runningAborts.set(agentName, abort);

  let stepCount = 0;

  try {
    await agentExecuteStream(
      agentName,
      task,
      (event: AgentStreamEvent) => {
        if (event.type === "step") {
          stepCount++;
          const msg = (event.data.message as string) || `Step ${stepCount}`;
          stepsDiv.innerHTML += `<div class="agent-step-item" style="font-size:12px; color:var(--text-muted); margin:2px 0;">▸ ${escapeHtml(msg)}</div>`;
        } else if (event.type === "result") {
          const result = event.data.result as string;
          resultDiv.style.display = "block";
          resultDiv.textContent = result || JSON.stringify(event.data, null, 2);
        } else if (event.type === "error") {
          resultDiv.style.display = "block";
          resultDiv.style.color = "var(--error)";
          resultDiv.textContent = `Error: ${event.data.error ?? "Unknown error"}`;
        }
      },
      { signal: abort.signal, model: runtimeSettings?.default_model },
    );

    if (!resultDiv.textContent) {
      resultDiv.style.display = "block";
      resultDiv.textContent = "Completed (no result text).";
    }
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      resultDiv.style.display = "block";
      resultDiv.textContent = "⏹ Cancelled.";
    } else {
      resultDiv.style.display = "block";
      resultDiv.style.color = "var(--error)";
      resultDiv.textContent = `Error: ${err instanceof Error ? err.message : String(err)}`;
    }
  } finally {
    runningAborts.delete(agentName);
    execBtn.disabled = false;
    execBtn.style.display = "";
    cancelBtn.style.display = "none";
    stepsDiv.innerHTML = stepsDiv.innerHTML.replace(/<span class="spinner"><\/span>\s*/, "");
  }
}

function escapeHtml(str: string): string {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
