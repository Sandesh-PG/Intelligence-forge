# Feature 05: Research Chatbot Interface, GraphRAG Q&A Engine & Persistent Chat History

## 1. Execution Guardrails (Mandatory Rules for Agent)
- **NO BACKGROUND SERVERS:** Do NOT start `uvicorn`, `npm run dev`, or any long-running process.
- **NO AUTO-INSTALL:** Do NOT run `pip install`, `npm install`, or any package manager commands. Use Python's standard library `sqlite3` for chat persistence and `httpx` (already installed) for Ollama LLM synthesis.
- **FAST SYNCHRONOUS COMMANDS ONLY:** Only run `backend\.venv\Scripts\python.exe -m pytest -v`, `npx tsc --noEmit`, and `npm run lint`.
- **REMOVE GRAPH VISUALIZATION FROM UI:** Do NOT render any entity-relationship graph canvas, node-link diagram, or graph inspection tabs in the frontend. Keep Neo4j strictly as a backend GraphRAG retrieval engine.

---

## 2. Backend Implementation Plan (Chat Persistence + GraphRAG Q&A + Test Isolation)

### File 1: `backend/app/schemas/chat.py` (Create)
Define Pydantic v2 models for chat sessions, messages, citations, and requests:
- `CitationItem(BaseModel)`:
  - `doc_id: str`
  - `filename: str`
  - `page_number: Optional[int] = None`
  - `snippet: str`
- `ChatMessageOut(BaseModel)`:
  - `id: str`
  - `session_id: str`
  - `role: str` (`"user" | "assistant"`)
  - `content: str`
  - `citations: list[CitationItem] = []`
  - `created_at: str`
- `ChatSessionSummary(BaseModel)`:
  - `id: str`
  - `title: str`
  - `doc_ids: list[str] = []`
  - `message_count: int = 0`
  - `updated_at: str`
  - `created_at: str`
- `ChatSessionDetail(BaseModel)`:
  - `id: str`
  - `title: str`
  - `doc_ids: list[str] = []`
  - `messages: list[ChatMessageOut] = []`
  - `updated_at: str`
  - `created_at: str`
- `CreateChatRequest(BaseModel)`:
  - `title: Optional[str] = "New Research Chat"`
  - `doc_ids: list[str] = []`
- `SendMessageRequest(BaseModel)`:
  - `content: str`
  - `doc_ids: Optional[list[str]] = None` (optional override/attachment of papers to scope the query)
- `SendMessageResponse(BaseModel)`:
  - `session: ChatSessionSummary`
  - `user_message: ChatMessageOut`
  - `assistant_message: ChatMessageOut`

### File 2: `backend/app/services/chat_store.py` (Create)
Implement SQLite persistence using Python's built-in `sqlite3` stored at `settings.data_dir / "chats.db"` (ensure parent directory is created automatically):
- Tables:
  - `chat_sessions(id TEXT PRIMARY KEY, title TEXT NOT NULL, doc_ids_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)`
  - `chat_messages(id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, citations_json TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE)`
- Methods:
  - `init_db()` (enables `PRAGMA foreign_keys = ON` and creates tables if not exists)
  - `create_session(title: str, doc_ids: list[str]) -> ChatSessionDetail`
  - `list_sessions() -> list[ChatSessionSummary]` (ordered by `updated_at DESC`)
  - `get_session(session_id: str) -> Optional[ChatSessionDetail]`
  - `update_session_docs(session_id: str, doc_ids: list[str]) -> Optional[ChatSessionSummary]`
  - `delete_session(session_id: str) -> bool`
  - `append_message(session_id: str, role: str, content: str, citations: list[CitationItem], auto_title_from_first_user_msg: bool = False) -> ChatMessageOut`

### File 3: `backend/app/services/graphrag_qa_service.py` (Create)
Implement Hybrid GraphRAG Retrieval + Ollama Synthesis:
- `@staticmethod async def answer_question(question: str, doc_ids: list[str], chat_history: list[ChatMessageOut]) -> tuple[str, list[CitationItem]]`:
  1. **Retrieve Local Extracted Knowledge:** Load extracted JSONs from `settings.extracted_storage_dir` for the scoped `doc_ids` (or all extracted docs if `doc_ids` is empty). Collect document summaries, matching entities, and relationship evidence quotes matching keywords from `question`.
  2. **Retrieve Neo4j AuraDB Graph Context:** If `settings.neo4j_uri` is configured, query Neo4j AuraDB via `neo4j_driver.get_driver()` for matching `Entity` nodes (`toLower(n.name) CONTAINS term OR toLower(n.description) CONTAINS term`) and their 1-hop relationships `(n)-[r]-(m)` scoped to `doc_ids` when provided. Gracefully fall back to local extracted context if Neo4j is unreachable.
  3. **Build Grounded Prompt & Call Ollama:** Send system prompt instructing the LLM (`settings.ollama_model` at `settings.ollama_base_url`) to answer strictly using the retrieved paper summaries, graph facts, and evidence quotes, citing sources inline like `[Filename, p. X]`. Include the last 6 messages of `chat_history` for multi-turn follow-up context.
  4. **Graceful Offline Fallback:** If Ollama is unavailable or times out, synthesize a clean structured response directly from the top matching retrieved evidence snippets and summary so the chat never crashes.
  5. Return `(answer_text, citations_list)`.

### File 4: `backend/app/routers/chat.py` (Create)
Expose REST endpoints registered in `backend/app/main.py`:
- `GET /api/chats` -> `list[ChatSessionSummary]`
- `POST /api/chats` -> `ChatSessionDetail`
- `GET /api/chats/{session_id}` -> `ChatSessionDetail` (`404` if missing)
- `PATCH /api/chats/{session_id}/documents` -> updates attached `doc_ids` for the session
- `DELETE /api/chats/{session_id}` -> deletes session and its messages (`204` or `{"deleted": True}`)
- `POST /api/chats/{session_id}/messages` -> persists user message, calls `GraphRAGQAService.answer_question(...)`, persists assistant message with citations, auto-updates session title on first message, and returns `SendMessageResponse`.

### File 5: `backend/app/main.py` (Modify)
- Register `chat.router` alongside `upload`, `documents`, and `graph` routers.

### File 6: `backend/tests/conftest.py` & `backend/tests/test_chat_router.py` (Create/Modify)
- **Fix Test Pollution:** In `backend/tests/conftest.py`, add an `autouse=True` fixture that points `settings.upload_storage_dir`, `settings.extracted_storage_dir`, and the SQLite `chats.db` path to `tmp_path` during `pytest` runs so tests never write mock PDFs (`p.pdf`, `valid.pdf`, etc.) into live `backend/data/`.
- In `backend/tests/test_chat_router.py`, add unit tests covering session creation, listing, message persistence in SQLite, GraphRAG Q&A response with mocked LLM/Neo4j, and session deletion.

---

## 3. Frontend Implementation Plan (Focused 2-Pane Research Chatbot UI)

### File 7: `frontend/src/types/chat.ts` (Create)
Define TypeScript interfaces matching backend schemas (`DocumentItem`, `CitationItem`, `ChatMessage`, `ChatSessionSummary`, `ChatSessionDetail`, `SendMessageResponse`).

### File 8: `frontend/src/lib/api.ts` (Modify)
Replace graph-canvas API helpers with clean Chat + Document API helpers:
- `fetchChats(): Promise<ChatSessionSummary[]>`
- `createChat(title?: string, docIds?: string[]): Promise<ChatSessionDetail>`
- `fetchChatDetail(sessionId: string): Promise<ChatSessionDetail>`
- `updateChatDocuments(sessionId: string, docIds: string[]): Promise<ChatSessionSummary>`
- `deleteChat(sessionId: string): Promise<void>`
- `sendChatMessage(sessionId: string, content: string, docIds?: string[]): Promise<SendMessageResponse>`
- `fetchDocuments(): Promise<DocumentItem[]>`
- `uploadDocuments(files: File[]): Promise<unknown>`

### File 9: `frontend/src/components/ChatSidebar.tsx` (Create)
- Left sidebar (`w-72 border-r border-zinc-800 bg-zinc-950 flex flex-col shrink-0`):
  - **+ New Chat** primary button at top.
  - **Chat History List:** Displays saved DB conversations (`title`, relative timestamp, message count badge) with active selection highlight and hover delete (`Trash`) icon.
  - **Uploaded Papers Section (Bottom half of sidebar):** Lists ingested PDFs with extraction status pill (`Ready` / `Processing`), a quick **+ Upload PDF** trigger, and checkboxes/pills to attach or detach papers from the active chat session.

### File 10: `frontend/src/components/ChatMessageBubble.tsx` (Create)
- Clean conversational message renderer:
  - User messages aligned right (`bg-blue-600 text-white rounded-2xl px-4 py-2.5`).
  - Assistant messages aligned left (`bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-2xl px-4 py-3`) with formatted paragraphs/lists and collapsible **Sources & Page Citations** pills (`filename · p. X` + hover/expandable evidence snippet).

### File 11: `frontend/src/components/ChatWorkspace.tsx` (Create)
- Main center chat column (`flex-1 flex flex-col bg-[#09090b] min-w-0`):
  - **Top Context Header (`h-14 border-b border-zinc-800 px-6 flex items-center justify-between`):**
    - Active chat title + attached paper pills (with `+ Attach Paper` / `+ Upload PDF` button).
  - **Empty / Welcome State (when no messages yet):**
    - Clean centered prompt card with drag-and-drop PDF upload box + 4 clickable starter questions (e.g., *"Summarize the main contributions of my uploaded paper"*, *"What methods and datasets are evaluated?"*, *"List the key experimental results and metrics"*).
  - **Scrollable Message Feed:** Renders `ChatMessageBubble` items + animated `Thinking & querying knowledge base...` indicator while awaiting response.
  - **Bottom Composer Bar:** Auto-resizing textarea (`Enter` to send, `Shift+Enter` for newline), inline **Attach PDF (`📎`)** button that uploads directly into the active chat, and **Send** button.

### File 12: `frontend/src/app/page.tsx` (Replace)
- Replace the 3-pane graph explorer page with the clean **2-Pane Research Chatbot Layout** (`ChatSidebar` + `ChatWorkspace` + `UploadModal`), completely free of any entity-relationship graph visualization.
- Clean up unused graph visualization components (`KnowledgeGraphCanvas.tsx`, `ExtractionTablesView.tsx`, `InspectorPanel.tsx`) if no longer referenced.

---

## 4. Progress Tracker Update (`progress-tracker.md`)
Update `progress-tracker.md`:
- Mark **Feature 05: Research Chatbot Interface, GraphRAG Q&A Engine & Persistent Chat History** as `Completed`.
- Document SQLite chat persistence (`backend/data/chats.db`), `/api/chats` endpoints, GraphRAG Q&A synthesis, test isolation via `tmp_path`, and the 2-pane chatbot UI.

---

## 5. Verification Checklist
1. `backend\.venv\Scripts\python.exe -m pytest -v` — all tests pass without creating files in `backend/data/`.
2. `cd frontend && npx tsc --noEmit` — 0 TypeScript errors.
3. `cd frontend && npm run lint` — 0 ESLint errors.