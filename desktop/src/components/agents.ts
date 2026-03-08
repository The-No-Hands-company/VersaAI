/** Agents view — list and execute agents. */

import { agentList, agentExecute, type AgentInfo } from "../api";

let agents: AgentInfo[] = [];
let loadError: string | null = null;
let containerEl: HTMLElement | null = null;

export function renderAgents(el: HTMLElement) {
  containerEl = el;
  el.innerHTML = `
    <h1 class="heading">Agents</h1>
    <div id="agents-grid" class="agents-grid">
      <p style="color: var(--text-muted)">Loading agents…</p>
    </div>
  `;

  loadAgents();
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
      </div>
      <div class="agent-result" id="agent-result-${i}" style="display:none; margin-top:8px; font-size:13px; color:var(--text-secondary); white-space:pre-wrap;"></div>
    </div>
  `,
    )
    .join("");

  // Bind execute buttons
  grid.querySelectorAll(".btn--exec").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const agentName = (e.currentTarget as HTMLElement).dataset.agent!;
      const card = (e.currentTarget as HTMLElement).closest(".agent-card")!;
      const input = card.querySelector<HTMLInputElement>(".agent-task-input")!;
      const resultDiv = card.querySelector<HTMLElement>(".agent-result")!;
      const task = input.value.trim();
      if (!task) return;

      (e.currentTarget as HTMLButtonElement).disabled = true;
      resultDiv.style.display = "block";
      resultDiv.textContent = "Running…";

      try {
        const result = await agentExecute(agentName, task);
        resultDiv.textContent = JSON.stringify(result, null, 2);
      } catch (err) {
        resultDiv.textContent = `Error: ${err instanceof Error ? err.message : String(err)}`;
        resultDiv.style.color = "var(--error)";
      } finally {
        (e.currentTarget as HTMLButtonElement).disabled = false;
      }
    });
  });
}

function escapeHtml(str: string): string {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
