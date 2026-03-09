/** Settings view — runtime configuration management. */

import { getSettings, updateSettings, listModels, type SettingsView, type ModelInfo } from "../api";

let containerEl: HTMLElement | null = null;
let current: SettingsView | null = null;
let models: ModelInfo[] = [];
let saving = false;

export function renderSettings(el: HTMLElement) {
  containerEl = el;
  el.innerHTML = `
    <h1 class="heading">Settings</h1>
    <div id="settings-content">
      <p style="color: var(--text-muted)">Loading settings…</p>
    </div>
  `;
  loadSettings();
}

async function loadSettings() {
  const content = containerEl?.querySelector("#settings-content");
  if (!content) return;

  try {
    const [s, m] = await Promise.all([getSettings(), listModels()]);
    current = s;
    models = m;
    renderForm(content as HTMLElement);
  } catch (err) {
    content.innerHTML = `<p style="color: var(--error)">Failed to load settings: ${err instanceof Error ? err.message : String(err)}</p>`;
  }
}

function renderForm(el: HTMLElement) {
  if (!current) return;

  const providerOptions = Object.keys(current.providers)
    .map((p) => `<option value="${esc(p)}" ${p === current!.default_provider ? "selected" : ""}>${esc(p)}</option>`)
    .join("");

  const modelOptions = models
    .map((m) => `<option value="${esc(m.name)}" ${m.name === current!.default_model ? "selected" : ""}>${esc(m.name)} (${esc(m.provider)})</option>`)
    .join("");

  el.innerHTML = `
    <form id="settings-form" class="settings-form">
      <fieldset class="settings-group">
        <legend>Model Configuration</legend>

        <label class="settings-label">
          Provider
          <select id="s-provider" class="settings-input">${providerOptions}</select>
        </label>

        <label class="settings-label">
          Model
          <select id="s-model" class="settings-input">${modelOptions}</select>
        </label>

        <label class="settings-label">
          Temperature
          <input id="s-temp" type="number" min="0" max="2" step="0.05" class="settings-input"
            value="${current.temperature}" />
        </label>

        <label class="settings-label">
          Max Tokens
          <input id="s-max-tokens" type="number" min="1" max="128000" step="1" class="settings-input"
            value="${current.max_tokens}" />
        </label>
      </fieldset>

      <fieldset class="settings-group">
        <legend>RAG</legend>

        <label class="settings-label settings-label--inline">
          <input id="s-rag-enabled" type="checkbox" ${current.rag_enabled ? "checked" : ""} />
          Enable RAG
        </label>

        <label class="settings-label">
          Top-K Results
          <input id="s-rag-topk" type="number" min="1" max="50" step="1" class="settings-input"
            value="${current.rag_top_k}" />
        </label>
      </fieldset>

      <fieldset class="settings-group">
        <legend>Provider Status</legend>
        <div class="providers-status">
          ${Object.entries(current.providers)
            .map(
              ([name, info]) => `
            <div class="provider-row">
              <span class="indicator ${info.enabled ? "online" : "offline"}"></span>
              <span>${esc(name)}</span>
            </div>
          `,
            )
            .join("")}
        </div>
      </fieldset>

      <div class="settings-actions">
        <button type="submit" class="btn btn--primary" id="btn-save">Save</button>
        <span id="settings-msg" style="margin-left:8px; font-size:13px;"></span>
      </div>
    </form>
  `;

  el.querySelector("#settings-form")!.addEventListener("submit", handleSave);
}

async function handleSave(e: Event) {
  e.preventDefault();
  if (saving) return;
  saving = true;

  const btn = containerEl?.querySelector("#btn-save") as HTMLButtonElement;
  const msg = containerEl?.querySelector("#settings-msg") as HTMLElement;
  btn.disabled = true;
  msg.textContent = "Saving…";
  msg.style.color = "";

  const provider = (containerEl?.querySelector("#s-provider") as HTMLSelectElement).value;
  const model = (containerEl?.querySelector("#s-model") as HTMLSelectElement).value;
  const temperature = parseFloat((containerEl?.querySelector("#s-temp") as HTMLInputElement).value);
  const max_tokens = parseInt((containerEl?.querySelector("#s-max-tokens") as HTMLInputElement).value, 10);
  const rag_enabled = (containerEl?.querySelector("#s-rag-enabled") as HTMLInputElement).checked;
  const rag_top_k = parseInt((containerEl?.querySelector("#s-rag-topk") as HTMLInputElement).value, 10);

  try {
    current = await updateSettings({
      default_provider: provider,
      default_model: model,
      temperature,
      max_tokens,
      rag_enabled,
      rag_top_k,
    });
    msg.textContent = "Saved ✓";
    msg.style.color = "var(--success, #4caf50)";
  } catch (err) {
    msg.textContent = `Error: ${err instanceof Error ? err.message : String(err)}`;
    msg.style.color = "var(--error)";
  } finally {
    btn.disabled = false;
    saving = false;
  }
}

function esc(str: string): string {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
