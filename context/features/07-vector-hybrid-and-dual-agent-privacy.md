# Feature 07: Fast Ingestion, Vector Hybrid Retrieval, Dual-Agent Routing & Zero-Leakage Privacy Firewall

## 1. Execution Guardrails (STRICT ANTI-HANG RULES — MANDATORY)
- **NEVER RUN BACKGROUND TASKS:** Do NOT spawn background shells, daemons, servers (`uvicorn`, `npm run dev`, `next start`), or detached processes under any circumstance. Every shell command MUST be foreground-only and exit immediately.
- **NO AUTO-INSTALL:** Do NOT run `pip install`, `npm install`, or any package manager commands. Use `httpx` (already installed) for Ollama `/api/embeddings` + DuckDuckGo search, and pure-Python cosine similarity + Neo4j AuraDB `vector.similarity.cosine` / list properties.
- **ALLOWED VERIFICATION COMMANDS ONLY:**
  1. `backend\.venv\Scripts\python.exe -m pytest -v`
  2. `cd frontend && npx tsc --noEmit`
  3. `cd frontend && npm run lint`

---

## 2. Speed & Retrieval Bug Fixes (Ingestion + Auto-Polling)

### Fix A: Fast Digital-Text PDF Parsing (Drop 2-Min Delay to <10s)
- In `backend/app/services/pdf_parser.py` (or `docling_service.py` / `extraction_orchestrator.py`):
  - Configure Docling `PdfPipelineOptions(do_ocr=False, do_table_structure=False)` by default so digital-text research PDFs do not trigger heavy 770-layer CPU vision/OCR inference.
  - Ensure **every page's full text** (`page_number`, `text`) is preserved in the extracted JSON artifact (`pages: list[{"page_number": int, "text": str}]`) alongside `summary`, `entities`, and `relationships`.
  - When running LLM entity/relationship extraction, batch pages into ~4,000-character windows (with `[Page X]` markers) so a 5-page paper completes in 1–2 Ollama calls instead of 5+ sequential calls.

### Fix B: Frontend 3-Second Auto-Polling for Processing Papers
- In `frontend/src/app/page.tsx`:
  - Add a `useEffect` polling hook that checks if any document in `documents` has `extraction_status !== "completed"` (e.g., `"processing"`, `"queued"`, `"uploaded"`).
  - While any document is still processing, poll `fetchDocuments(activeSessionId)` every `3000ms` and automatically clear the interval once all attached papers reach `"completed"`.
- In `backend/app/routers/documents.py`:
  - Ensure `GET /api/documents` resolves `extraction_status` consistently with `GET /api/documents/{doc_id}/status` (returning `"completed"` whenever the document status is completed or `{doc_id}.json` exists on disk).

---

## 3. Vector Embeddings + Dual-Agent + Zero-Leakage Privacy Architecture

### File 1: `backend/app/core/config.py` (Modify)
Add optional settings with safe defaults:
- `embedding_model: str = "nomic-embed-text"`
- `enable_global_web_agent: bool = True`
- `web_search_timeout: float = 8.0`

### File 2: `backend/app/services/embedding_service.py` (Create)
- `@staticmethod async def embed_text(text: str) -> list[float]`:
  - Calls Ollama `POST {settings.ollama_base_url}/api/embeddings` (`{"model": settings.embedding_model, "prompt": text[:2000]}`) with `timeout=5.0`.
  - If Ollama is unreachable or the embedding model is not pulled locally, falls back deterministically to a 128-dimensional normalized token/character-ngram hash vector (`_fallback_hash_embedding(text, dim=128)`) so vector embeddings always succeed without blocking ingestion.
- `@staticmethod def cosine_similarity(a: list[float], b: list[float]) -> float`:
  - Computes cosine similarity safely (`0.0` if mismatched lengths or zero norm).

### File 3: `backend/app/services/graph_persistence_service.py` (Modify)
- **Persist Vectors on `:Entity` and `:Chunk` Nodes:**
  - When syncing/persisting a document (`persist_document_graph(doc_id)`):
    1. Split the document's `pages` text into overlapping ~650-character page-aware chunks (`chunk_id = f"{doc_id}::p{page_num}::c{idx}"`).
    2. Generate vector embeddings via `EmbeddingService.embed_text(...)` for every `:Chunk` and every `:Entity`.
    3. Store `embedding` on `:Entity` nodes and `MERGE (c:Chunk {chunk_id: $chunk_id})` with `c.doc_id`, `c.filename`, `c.page_number`, `c.text`, `c.embedding`, linked via `MERGE (p)-[:HAS_CHUNK]->(c)`.
  - Update `delete_document_graph(doc_id)` to also delete all `:Chunk` nodes where `c.doc_id = $doc_id`.
- **Hybrid Vector + Graph Retrieval (`vector_and_graph_search`):**
  - `@staticmethod async def retrieve_hybrid_context(question: str, doc_ids: list[str], top_k: int = 8) -> dict`:
    - Embeds `question` via `EmbeddingService.embed_text(question)`.
    - Queries Neo4j AuraDB (and falls back to local extracted JSON chunks/entities if Neo4j is offline) scoped **strictly** to `doc_id IN $doc_ids`:
      - Ranks `:Chunk` passages by cosine similarity (`vector.similarity.cosine` or Python cosine fallback) + keyword overlap, returning top `top_k` passages with exact `doc_id`, `filename`, `page_number`, and `text`.
      - Ranks `:Entity` nodes by cosine similarity and expands 1-hop relationships `(e)-[r]-(neighbor)` scoped to `r.doc_id IN $doc_ids`.

### File 4: `backend/app/services/privacy_guard.py` (Create — Zero-Leakage Firewall)
- `PrivacyCheckResult(BaseModel)`:
  - `sanitized_query: str`
  - `is_safe: bool`
  - `redacted_terms: list[str] = []`
  - `blocked_reason: Optional[str] = None`
- `@staticmethod def sanitize_for_public_web(user_question: str, missing_concepts: list[str], local_chunks: list[str], local_filenames: list[str]) -> PrivacyCheckResult`:
  - **Strict Sanitization Pipeline:**
    1. Strips all local filenames (with and without `.pdf`), `doc_id` UUIDs, email addresses, file paths, and author/institution names found in the local paper metadata.
    2. Extracts all 4-word n-grams from `local_chunks` (lowercased, punctuation-stripped); removes or blocks any phrase in the candidate search query that matches a 4+ word sequence from the uploaded local papers.
    3. Builds a concise, abstract public search query (`<= 12` words) focused strictly on the missing general/external concept(s).
    4. Final verification gate: if `sanitized_query` is empty (`< 3` chars) or still shares any 4-word n-gram with `local_chunks`, sets `is_safe = False` and `blocked_reason = "Blocked to prevent local document leakage"`.

### File 5: `backend/app/services/global_web_agent.py` (Create — Agent 2)
- `WebCitation(BaseModel)`: `title: str`, `url: str`, `snippet: str`
- `@staticmethod async def search_and_synthesize(sanitized_query: str, user_question: str) -> tuple[str, list[WebCitation]]`:
  - Uses `httpx.AsyncClient(timeout=settings.web_search_timeout)` to query DuckDuckGo Instant Answer API (`https://api.duckduckgo.com/?q=...&format=json&no_html=1&skip_disambig=1`) and/or lightweight HTML results (`https://html.duckduckgo.com/html/?q=...`) using **exclusively** `sanitized_query`.
  - Extracts top 3–5 public web snippets + URLs (`WebCitation`), synthesizes a concise external summary via Ollama (or returns the structured web snippets if Ollama is offline), and returns `(web_summary, web_citations)`.

### File 6: `backend/app/services/graphrag_qa_service.py` & `backend/app/schemas/chat.py` (Modify — Dual-Agent Orchestrator)
- Update `ChatMessageOut` in `backend/app/schemas/chat.py`:
  - `citations: list[CitationItem] = []` (Local Paper Citations)
  - `web_citations: list[WebCitation] = []` (External Web Citations)
  - `agent_trace: Optional[dict] = None` (`{"local_agent_used": bool, "web_agent_used": bool, "privacy_verified": bool, "sanitized_query": Optional[str], "redacted_count": int}`)
- Update `SendMessageRequest` in `backend/app/schemas/chat.py`:
  - Add `allow_web_search: bool = True`
- Update `GraphRAGQAService.answer_question(...)` to execute the **2-Agent Workflow**:
  1. **Agent 1 (Local Grounded Agent):**
     - Retrieves hybrid vector chunks + Neo4j graph facts scoped strictly to `session.doc_ids`.
     - Asks local Ollama to answer strictly from the retrieved local chunks/graph and evaluate whether the uploaded papers fully cover the user's question (`COVERAGE: COMPLETE` vs `COVERAGE: INSUFFICIENT | MISSING: <abstract topic>`).
     - Note: With full-page `:Chunk` vectors across all pages (pages 1–5), specific facts on pages 3–5 (e.g., *Erica, Sophia, AEG bot, AI2 Platform, BT Group*) are now found directly by Agent 1 with `COVERAGE: COMPLETE` and zero web search needed.
  2. **Privacy Firewall + Agent 2 (Global Web Agent):**
     - Triggered **only** when `COVERAGE: INSUFFICIENT` (or `doc_ids` is empty and user asks a factual question) AND `allow_web_search` is `True`.
     - Passes candidate query through `PrivacyGuard.sanitize_for_public_web(...)`.
     - If `privacy_result.is_safe` is `True`, invokes `GlobalWebAgent.search_and_synthesize(privacy_result.sanitized_query, question)`.
     - Formats the final response clearly distinguishing **From Uploaded Research Papers** (with `[Filename, p. X]` citations) and **External Web Context** (with web source links).

### File 7: `backend/app/services/chat_store.py` & `backend/app/routers/chat.py` (Modify)
- Safely add `web_citations_json TEXT DEFAULT '[]'` and `agent_trace_json TEXT DEFAULT '{}'` to `chat_messages` (running `ALTER TABLE` inside `try/except` in `init_db()` so existing `chats.db` upgrades seamlessly without data loss).
- Pass `allow_web_search` from `POST /api/chats/{session_id}/messages` into `GraphRAGQAService.answer_question(...)`.

### File 8: `backend/tests/test_dual_agent_privacy.py` (Create)
Add unit & integration tests verifying:
1. Full-page chunk vector indexing & cosine retrieval across multi-page documents (verifying facts on page 4/5 are retrieved with accurate page numbers).
2. **Zero-Leakage Privacy Firewall:** Verifies filenames, author names, and 4+ word verbatim passages from uploaded PDFs are stripped/blocked and never passed to `GlobalWebAgent`.
3. **Dual-Agent Routing:** Verifies `GlobalWebAgent` is NOT invoked when local chunks fully answer the question, and IS invoked (with sanitized query only) when information is missing from local papers.

---

## 4. Frontend File Manifest (Auto-Polling + Dual-Agent & Privacy UI)

### File 9: `frontend/src/types/chat.ts` & `frontend/src/lib/api.ts` (Modify)
- Add `WebCitation` (`title`, `url`, `snippet`) and `AgentTrace` (`local_agent_used`, `web_agent_used`, `privacy_verified`, `sanitized_query`, `redacted_count`) to `ChatMessage`.
- Add `allowWebSearch?: boolean` parameter to `sendChatMessage(...)`.

### File 10: `frontend/src/components/ChatMessageBubble.tsx` & `frontend/src/components/ChatWorkspace.tsx` & `frontend/src/app/page.tsx` (Modify)
- In `frontend/src/app/page.tsx`:
  - Add the 3-second polling `useEffect` while any attached document has `extraction_status !== "completed"` so `Processing` flips to `Ready` automatically.
- In `frontend/src/components/ChatMessageBubble.tsx`:
  - Display **Verified Local Paper Citations** (`Filename · p. X`) and, when `web_citations` are present, a separate **External Web Sources** section with clickable links.
  - Display a compact **Privacy Shield Badge** (`Local Grounded` or `Web Fallback · Privacy Verified`) on assistant bubbles.
- In `frontend/src/components/ChatWorkspace.tsx`:
  - Add a clean **Web Search Fallback: ON / OFF** toggle button in the composer toolbar so users can switch between Hybrid Local+Web mode and strict Air-Gapped Local-Only mode anytime.

---

## 5. Progress Tracker Update (`progress-tracker.md`)
Update `progress-tracker.md`:
- Mark **Feature 07: Fast Ingestion, Vector Hybrid Retrieval, Dual-Agent Routing & Zero-Leakage Privacy Firewall** as `Completed`.
- Summarize the Docling speed optimization, 3s UI auto-polling, Neo4j `:Chunk`/`:Entity` vector embeddings, Local + Global Web dual-agent orchestration, and zero-leakage privacy firewall tests.

---

## 6. Verification Checklist
1. `backend\.venv\Scripts\python.exe -m pytest -v` — all tests pass (including `test_dual_agent_privacy.py`).
2. `cd frontend && npx tsc --noEmit` — 0 TypeScript errors.
3. `cd frontend && npm run lint` — 0 ESLint errors.