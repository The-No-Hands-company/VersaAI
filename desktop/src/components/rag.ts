/** RAG / Knowledge view — ingest documents, query the knowledge base, and browse ingested docs. */

import { ragIngest, ragQuery, ragStats, ragDocuments, type RagStats, type RagDocument } from "../api";

let containerEl: HTMLElement | null = null;

export function renderRag(el: HTMLElement) {
  containerEl = el;
  el.innerHTML = `
    <h1 class="heading">Knowledge Base</h1>

    <div id="rag-stats-bar" class="rag-stats-bar">
      <span style="color:var(--text-muted)">Loading stats…</span>
    </div>

    <section class="rag-section">
      <h2>Ingest Document</h2>
      <textarea id="rag-ingest-input" class="rag-textarea"
        placeholder="Paste text to add to the knowledge base…"></textarea>
      <button id="rag-ingest-btn" class="btn btn--primary">Ingest</button>
      <div id="rag-ingest-status" style="margin-top:8px; font-size:13px; color:var(--text-secondary);"></div>
    </section>

    <section class="rag-section">
      <h2>Query Knowledge</h2>
      <textarea id="rag-query-input" class="rag-textarea" rows="2"
        placeholder="Ask a question…"></textarea>
      <button id="rag-query-btn" class="btn btn--primary">Search</button>
      <div id="rag-results" class="rag-results"></div>
    </section>

    <section class="rag-section">
      <h2>Ingested Documents</h2>
      <div id="rag-doc-list" class="rag-doc-list">
        <span style="color:var(--text-muted);font-size:13px;">Loading…</span>
      </div>
    </section>
  `;

  // Ingest
  el.querySelector<HTMLButtonElement>("#rag-ingest-btn")!
    .addEventListener("click", handleIngest);

  // Query
  el.querySelector<HTMLButtonElement>("#rag-query-btn")!
    .addEventListener("click", handleQuery);

  // Load stats & documents
  loadStats();
  loadDocuments();
}

// ---------------------------------------------------------------------------
async function loadStats() {
  const bar = containerEl?.querySelector<HTMLElement>("#rag-stats-bar");
  if (!bar) return;
  try {
    const s: RagStats = await ragStats();
    bar.innerHTML = `
      <div class="rag-stats-bar__item">Documents <span class="rag-stats-bar__value">${s.total_documents ?? 0}</span></div>
      <div class="rag-stats-bar__item">Chunks <span class="rag-stats-bar__value">${s.total_chunks ?? 0}</span></div>
      <div class="rag-stats-bar__item">Queries <span class="rag-stats-bar__value">${s.total_queries ?? 0}</span></div>
    `;
  } catch {
    bar.innerHTML = '<span style="color:var(--text-muted);font-size:12px;">Stats unavailable</span>';
  }
}

async function loadDocuments() {
  const listEl = containerEl?.querySelector<HTMLElement>("#rag-doc-list");
  if (!listEl) return;
  try {
    const res = await ragDocuments(50);
    const docs: RagDocument[] = res.documents ?? [];
    if (docs.length === 0) {
      listEl.innerHTML = '<span style="color:var(--text-muted);font-size:13px;">No documents ingested yet.</span>';
      return;
    }
    listEl.innerHTML = docs
      .map((d) => {
        const preview = (d.content ?? "").slice(0, 80).replace(/\n/g, " ");
        return `
          <div class="rag-doc-row">
            <span class="rag-doc-row__id">${escapeHtml(d.id?.slice(0, 10) ?? "—")}</span>
            <span class="rag-doc-row__preview">${escapeHtml(preview || "(no preview)")}</span>
          </div>`;
      })
      .join("");
  } catch {
    listEl.innerHTML = '<span style="color:var(--text-muted);font-size:13px;">Could not load documents.</span>';
  }
}

async function handleIngest() {
  const input =
    containerEl?.querySelector<HTMLTextAreaElement>("#rag-ingest-input");
  const status = containerEl?.querySelector<HTMLElement>("#rag-ingest-status");
  if (!input || !status) return;

  const text = input.value.trim();
  if (!text) return;

  status.textContent = "Ingesting…";
  status.style.color = "var(--text-secondary)";

  try {
    const res = await ragIngest(text);
    status.textContent = `✓ Ingested — ${JSON.stringify(res)}`;
    status.style.color = "var(--success)";
    input.value = "";
    // Refresh stats and document list
    loadStats();
    loadDocuments();
  } catch (err) {
    status.textContent = `✗ ${err instanceof Error ? err.message : String(err)}`;
    status.style.color = "var(--error)";
  }
}

async function handleQuery() {
  const input =
    containerEl?.querySelector<HTMLTextAreaElement>("#rag-query-input");
  const resultsEl = containerEl?.querySelector<HTMLElement>("#rag-results");
  if (!input || !resultsEl) return;

  const question = input.value.trim();
  if (!question) return;

  resultsEl.innerHTML = '<p style="color: var(--text-muted)">Searching…</p>';

  try {
    const res = await ragQuery(question, 5);
    const results = (res.results ?? res.documents ?? []) as Array<{
      document?: string;
      content?: string;
      score?: number;
    }>;

    if (results.length === 0) {
      resultsEl.innerHTML =
        '<p style="color: var(--text-muted)">No results found.</p>';
      return;
    }

    resultsEl.innerHTML = results
      .map(
        (r) => `
      <div class="rag-result">
        ${r.score != null ? `<div class="rag-result__score">Score: ${(r.score * 100).toFixed(1)}%</div>` : ""}
        <div class="rag-result__text">${escapeHtml(r.document ?? r.content ?? JSON.stringify(r))}</div>
      </div>
    `,
      )
      .join("");
  } catch (err) {
    resultsEl.innerHTML = `<p style="color: var(--error)">Error: ${escapeHtml(err instanceof Error ? err.message : String(err))}</p>`;
  }
}

function escapeHtml(str: string): string {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
