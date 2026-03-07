# Research Agent Design

The **Research Agent** addresses core LLM weaknesses (hallucination, knowledge cutoff) through advanced Retrieval-Augmented Generation (RAG) and self-correction.

## 1. Adaptive Retrieval (Smart Detective)

### Dynamic Query Decomposition

- MUST use **Planner Agent** to break complex queries into targeted sub-queries
- MUST NOT rely on single, long search queries for multi-faceted questions

### Multi-Source Integration (3-Tier Knowledge Base)

- **Tier 1 (Real-Time):** Live web search + proprietary/enterprise data
- **Tier 2 (Vector DB):** Internal documents using **Multimodal Embeddings** (text, images, code)
- **Tier 3 (Knowledge Graph/GraphRAG):** Entity relationships (e.g., "CEO of Company X when Product Y launched")

### Adaptive K-Value

- MUST dynamically adjust retrieved document count (`k`) based on query complexity and relevance scores
- Prevents information overload (too many irrelevant chunks) and insufficient context

## 2. Metacognition & Self-Correction (Skeptical Editor)

### Self-RAG/CRAG Loop (Generator-Critic Pattern)

1. **Generate:** Foundation Model creates response draft using retrieved documents
2. **Critique:** Specialized **Critic Agent** evaluates:
   - **Groundedness:** Every factual claim supported by sources?
   - **Relevance:** Draft directly answers user's query?
3. **Correct:** If critique fails, trigger corrective action:
   - Formulate new search query (Adaptive Retrieval)
   - Revise answer with new Chain-of-Thought prompt

### Confidence Scoring

- MUST associate every factual claim with **confidence score**
- If below threshold (e.g., 90%), auto-trigger new search OR flag with caveat to user

### Traceability (Audit Trail)

- MUST log entire reasoning path:
  - Original query → sub-queries → retrieved documents (URLs/citations) → critique → final decision
- Ensures **auditability** and helps diagnose failure modes

## 3. Synthesized Output (Coherent Storyteller)

### Explicit Citation

- All factual claims MUST include **inline, clickable citations** to source documents/URLs
- Builds user trust and enables verification

### Conflict Resolution

- If sources contradict, MUST NOT ignore conflict
- MUST: (1) Acknowledge contradiction, (2) Present conflicting viewpoints, (3) Cite source for each

### Structured Format

- MUST prioritize clear, scannable output: headings, tables, bullet points
- Makes complex information digestible
