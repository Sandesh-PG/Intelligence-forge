# Feature 06: Chat-Scoped Document Uploads & Isolated Retrieval

## 1. Execution Guardrails (STRICT ANTI-HANG RULES — MANDATORY)
- **NEVER RUN BACKGROUND TASKS:** Do NOT spawn background shells, daemons, servers (`uvicorn`, `npm run dev`, `next start`), or detached processes under any circumstance. Every shell command MUST be synchronous, foreground-only, and exit immediately.
- **HARD TIMEOUT ON EVERY COMMAND:** Never run a command that waits on user input, file watchers (`--watch`), or live network sockets without a timeout.
- **NO AUTO-INSTALL:** Do NOT run `pip install`, `npm install`, or any package manager commands.
- **ALLOWED VERIFICATION COMMANDS ONLY:** You are ONLY permitted to run these three exact foreground commands at the very end:
  1. `backend\.venv\Scripts\python.exe -m pytest -v`
  2. `cd frontend && npx tsc --noEmit`
  3. `cd frontend && npm run lint`
- **SKIP SLOW INTEGRATION HOOKS:** In pytest, mock `neo4j_driver` and Ollama HTTP calls so tests never wait on external network connections.
---

## 2. Architecture & Behavior Changes
1. **No Global Paper Pool in Chat Context:**
   - Every uploaded document belongs to the specific `session_id` in which it was uploaded.
   - If a chat session has **0 attached documents** (`doc_ids == []`), `GraphRAGQAService.answer_question(...)` must **NOT** fall back to querying all global extracted documents or global Neo4j nodes; instead, it informs the user that no papers are attached to this chat yet and prompts them to upload one.
2. **Session-Bound Upload Flow (`POST /api/upload`):**
   - Accept optional `session_id: Optional[str] = Form(default=None)` in `POST /api/upload`.
   - When `session_id` is passed and valid, automatically attach the newly uploaded `doc_id`s to that chat session in `chat_store` (appending to `doc_ids_json`).
   - Also persist `session_id` in the document metadata record so documents can be queried per session.
3. **Session-Scoped Document Listing (`GET /api/documents`):**
   - Add optional query parameter `session_id: Optional[str] = Query(default=None)`.
   - When `session_id` is provided, return **only** the documents attached to that chat session (`session.doc_ids`).
4. **Cascade Cleanup on Chat Deletion (`DELETE /api/chats/{session_id}`):**
   - When a chat session is deleted, check if any of its `doc_ids` are no longer referenced by any remaining chat session; if unreferenced, remove their local uploaded/extracted artifacts and delete their `doc_id` edges/orphaned nodes from Neo4j AuraDB so deleted chats leave zero stale data behind.

---

## 3. Backend File Manifest

### File 1: `backend/app/routers/upload.py` (Modify)
- Add optional `session_id: Optional[str] = Form(default=None)` parameter to `POST /api/upload`.
- After saving uploaded files and enqueuing background extraction, if `session_id` is provided:
  - Fetch the session from `chat_store.get_session(session_id)` and append the newly created `doc_id`(s) via `chat_store.update_session_docs(...)` (deduplicating while preserving order).
- Include `session_id` in the upload response payload if provided.

### File 2: `backend/app/routers/documents.py` (Modify)
- Add optional `session_id: Optional[str] = Query(default=None)` to `GET /api/documents`.
- When `session_id` is provided:
  - Look up `session = chat_store.get_session(session_id)`. If not found, return `[]` (or `404`).
  - Filter returned `DocumentItemResponse` items strictly to `doc.doc_id in set(session.doc_ids)`.

### File 3: `backend/app/services/graphrag_qa_service.py` (Modify)
- **Strict Session Isolation:**
  - If `not doc_ids` (i.e., the active chat has no papers attached):
    - Do **NOT** scan all files in `settings.extracted_storage_dir` and do **NOT** query global Neo4j nodes.
    - If the user message is a greeting or general conversational message, respond naturally via Ollama (or a clean welcome reply) noting that no research papers are attached to this chat yet and inviting them to attach a PDF using the paperclip button.
  - When `doc_ids` is non-empty:
    - Restrict local JSON loading strictly to `[f"{doc_id}.json" for doc_id in doc_ids]`.
    - Restrict Neo4j Cypher queries strictly to `WHERE any(id IN coalesce(n.source_doc_ids, []) WHERE id IN $doc_ids)` and relationships where `r.doc_id IN $doc_ids`.

### File 4: `backend/app/services/chat_store.py` & `backend/app/routers/chat.py` (Modify)
- Add helper `get_all_referenced_doc_ids() -> set[str]` in `chat_store.py`.
- In `DELETE /api/chats/{session_id}` (`backend/app/routers/chat.py`):
  - Capture the deleted session's `doc_ids` before deleting the session.
  - For each `doc_id` no longer present in `chat_store.get_all_referenced_doc_ids()`, clean up its local raw PDF, extracted JSON, metadata entry, and Neo4j nodes/relationships (`GraphPersistenceService.delete_document_graph(doc_id)`).

### File 5: `backend/app/services/graph_persistence_service.py` (Modify)
- Add `@staticmethod def delete_document_graph(doc_id: str) -> None`:
  - Removes relationships with `{doc_id: $doc_id}`, removes `$doc_id` from `n.source_doc_ids`, and deletes any `:Entity` nodes whose `source_doc_ids` list is now empty (`size(coalesce(n.source_doc_ids, [])) = 0`).

### File 6: `backend/tests/test_chat_router.py` (Modify)
- Add tests verifying:
  1. Uploading with `session_id` attaches `doc_id` exclusively to that chat session and `GET /api/documents?session_id=...` only returns that session's files (not another session's files).
  2. Querying a chat with `doc_ids=[]` does NOT leak data from another chat's documents.
  3. Deleting a chat cleans up unreferenced documents.

---

## 4. Frontend File Manifest (Chat-Scoped Document UI)

### File 7: `frontend/src/lib/api.ts` (Modify)
- Update `fetchDocuments(sessionId?: string): Promise<DocumentItem[]>` to call `GET /api/documents?session_id=${sessionId}` when `sessionId` is provided (and return `[]` if no active `sessionId` exists).
- Update `uploadDocuments(files: File[], sessionId?: string): Promise<unknown>` to append `formData.append("session_id", sessionId)` when `sessionId` is provided.

### File 8: `frontend/src/components/ChatSidebar.tsx` (Modify)
- Remove the global paper library behavior:
  - Bottom section becomes **Chat Papers ({documents.length})** showing **only** the papers uploaded/attached to the currently selected chat session.
  - Remove global cross-chat checkboxes; instead show each paper belonging to the active chat with its status badge (`Ready` / `Processing`) and a remove (`×`) button to detach it from the current chat.
  - Keep **+ Upload PDF** scoped directly to the active chat session.

### File 9: `frontend/src/components/UploadModal.tsx` & `frontend/src/components/ChatWorkspace.tsx` (Modify)
- Pass `activeSessionId` into `UploadModal` and `ChatWorkspace` inline file picker so every upload automatically binds to the active chat (if no chat exists yet, auto-create one via `createChat()` first, then upload with the new `session.id`).
- Ensure top header bar (`ChatWorkspace.tsx`) only displays papers attached to the active chat session.

### File 10: `frontend/src/app/page.tsx` (Modify)
- Whenever `activeSessionId` changes (or when **+ New Research Chat** is clicked):
  - Reset `documents` to `[]` immediately while loading `fetchDocuments(newSessionId)` so papers from a previous chat never flash or appear in a new chat.
  - Ensure uploading a PDF from anywhere in the UI binds strictly to `activeSessionId` and refreshes only that session's documents.

---

## 5. Progress Tracker Update (`progress-tracker.md`)
Update `progress-tracker.md`:
- Mark **Feature 06: Chat-Scoped Document Uploads & Isolated Retrieval** as `Completed`.
- Summarize the session-scoped upload binding, strict GraphRAG retrieval isolation, cascade cleanup on chat deletion, and updated verification metrics.

---

## 6. Verification Checklist
1. `backend\.venv\Scripts\python.exe -m pytest -v` — all tests pass.
2. `cd frontend && npx tsc --noEmit` — 0 TypeScript errors.
3. `cd frontend && npm run lint` — 0 ESLint errors.