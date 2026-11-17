# Progress Tracker — Intelligence Forge

Update this file after meaningful implementation changes and at the end of each AI coding session. Do not mark a feature complete until its acceptance criteria and required verification have passed.

## 1. Current Project State

- **Development approach:** Incremental, spec-driven AI-agent workflow.
- **Repository:** Single Git repository initialized at the project root.
- **Frontend:** Next.js application with TypeScript and Tailwind CSS; focused 2-pane Research Chatbot UI (`ChatSidebar` + `ChatWorkspace` + `UploadModal`) implemented and verified. Entity-relationship graph canvas removed from UI and Neo4j kept strictly as a backend GraphRAG engine.
- **Backend:** Python FastAPI backend with upload validation service, local storage service, local multimodal document extraction (`Docling` + `Ollama`), Neo4j AuraDB graph persistence, SQLite chat persistence (`backend/data/chats.db`), Hybrid GraphRAG Q&A engine, and document/chat exploration REST APIs implemented and verified.
- **Feature implementation:**
  - Feature 01 (`01-upload-validate.md`) completed, verified (17 backend tests + clean TS/ESLint), and pushed.
  - Feature 02 (`02-document-extraction.md`) completed and verified end-to-end (39 backend tests passing, clean TS/ESLint, and live E2E extraction on a 5-page research paper producing 25 entities and 21 relationships).
  - Feature 03 (`03-graph-persistence.md`) completed and verified (44 backend tests passing, live Neo4j AuraDB persistence and health verified).
  - Feature 04 (`04-frontend-workspace-and-graph-explorer.md`) completed and verified (45 backend pytest tests passing, clean TypeScript compilation, and 0 ESLint errors).
  - Feature 05 (`05-research-chatbot-and-session-persistence.md`) completed and verified (57 backend pytest tests passing, clean TypeScript compilation, and 0 ESLint errors).
  - Feature 06 (`06-session-scoped-documents.md`) completed and verified (60 backend pytest tests passing, clean TypeScript compilation, and 0 ESLint errors).
  - Feature 07 (`07-dual-agent-orchestrator-and-privacy-firewall.md`) completed and verified (Dual-Agent Orchestration with Local Grounded Agent and Global Web Agent, Zero-Leakage Privacy Firewall with 4-gram and token redaction).
  - Feature 08 (`08-session-export-and-final-docs.md`) completed (Markdown session export endpoint with verified local/web citations, frontend Export .md button with browser download, comprehensive production README, and progress tracker finalization).
- **Databases:** Neo4j graph persistence implemented and live-verified (Feature 03); SQLite chat persistence implemented (Feature 05); Qdrant vector database selected for future vector indexing.

## 2. Current Goal

All core features (01–08) are completed and production-ready. System ready for end-to-end demonstration and user evaluation.

## 3. Completed

- **Feature 08: Research Session Markdown Export & Final Production Documentation**
  - Backend Export Endpoint (`GET /api/chats/{session_id}/export` in `backend/app/routers/chat.py`):
    - Fetches session details with full message history via `chat_store.get_session_with_messages(session_id)` (returns 404 with standard error code if missing).
    - Resolves human-readable paper filenames from attached `session.doc_ids` via `orchestrator.metadata_store` and storage metadata.
    - Generates a clean, structured Markdown report featuring:
      - Title, session ID, timestamps, and attached research papers.
      - User and Assistant message turns.
      - Agent verification and trace metadata (`Local Grounded`, `Web Fallback`, `Privacy Verified`).
      - Local paper citations (`[Filename, p. X]: snippet`).
      - External web sources (`[Title](URL)`).
    - Returns `Response(content=markdown_text, media_type="text/markdown", headers={"Content-Disposition": 'attachment; filename="research-session-<id>.md"'})`.
  - Backend Export Unit & Integration Tests (`backend/tests/test_chat_router.py`):
    - Added `test_export_chat_session_markdown` verifying 404 for missing sessions, 200 with `text/markdown`, proper headers, session title, user/assistant turns, local paper citations, external web sources, and privacy trace indicators.
  - Frontend Export API & UI Integration:
    - Added `exportChatMarkdown(sessionId)` to `frontend/lib/api.ts` fetching the Markdown stream and parsing attachment filenames.
    - Updated `frontend/components/ChatWorkspace.tsx` with a compact **Export .md** button in the top navigation header (enabled when `activeChat.id` exists and `messages.length > 0`), which triggers a direct browser file download (`research-session-<id>.md`).
  - Comprehensive Final Documentation (`README.md`):
    - Completely overhauled `README.md` with: Core capabilities overview, ASCII system architecture diagram, environment setup instructions (`backend/.env`), local Ollama model setup, run instructions, and complete test verification suite commands.

- **Feature 07: Dual-Agent Orchestration & Zero-Leakage Privacy Firewall**
  - Local Grounded Agent (Agent 1):
    - Hybrid retrieval combining local paper chunks and 1-hop Neo4j AuraDB facts scoped strictly to attached session papers.
    - Evidence-sufficiency evaluation determining `COVERAGE: COMPLETE` or `COVERAGE: INSUFFICIENT`.
  - Global Web Agent (Agent 2):
    - Fallback web query synthesis via DuckDuckGo when internal paper coverage is insufficient and web search is enabled.
  - Zero-Leakage Privacy Firewall (`PrivacyGuard`):
    - Strict allowlist-based query sanitization removing local filenames, document IDs, and all 4-word verbatim passage n-grams before outbound external requests.
    - Fail-closed behavior preventing query transmission when proprietary content cannot be safely scrubbed.

- **Feature 06: Chat-Scoped Document Uploads & Isolated Retrieval**
  - Session-Bound Upload Flow (`POST /api/upload`):
    - Added optional `session_id: Optional[str] = Form(default=None)` parameter to `POST /api/upload`.
    - Automatically binds newly uploaded `doc_id`(s) to the specified chat session in `chat_store.update_session_docs(...)` without duplicates, and records `session_id` in document metadata records.
    - Updated `BatchUploadResponse` and `FileUploadResult` schemas with `session_id`.
  - Session-Scoped Document Listing (`GET /api/documents`):
    - Added optional query parameter `session_id: Optional[str] = Query(default=None)` to `GET /api/documents`.
    - Strictly filters returned `DocumentItemResponse` items to documents attached to that specific chat session (`session.doc_ids`).
  - Strict GraphRAG Session Isolation (`backend/app/services/graphrag_qa_service.py`):
    - When `not doc_ids` (no papers attached to the active chat), retrieval strictly bypasses disk artifact scans and global Neo4j queries; responds naturally to general conversation or prompts to attach a PDF without data leaks.
    - When `doc_ids` is non-empty, restricts local JSON loading strictly to `[f"{doc_id}.json" for doc_id in doc_ids]` and restricts Neo4j Cypher queries strictly to `WHERE r.doc_id IN $doc_ids` and `ANY(id IN coalesce(n.source_doc_ids, []) WHERE id IN $doc_ids)`.
  - Cascade Cleanup on Chat Deletion (`DELETE /api/chats/{session_id}`):
    - Added `chat_store.get_all_referenced_doc_ids() -> set[str]` helper.
    - On deleting a chat, any `doc_id` no longer referenced by any remaining chat session is automatically cleaned up: local raw PDF removed, extracted JSON artifact unlinked, metadata cleared, and orphaned Neo4j graph nodes and relationships purged via `GraphPersistenceService.delete_document_graph(doc_id)`.
  - Frontend Chat-Scoped Document UI:
    - Updated `fetchDocuments(sessionId?: string)` and `uploadDocuments(files, sessionId?: string)` in `frontend/src/lib/api.ts` and `frontend/services/uploadService.ts`.
    - `ChatSidebar.tsx`: Converted bottom panel to **Chat Papers ({documents.length})** displaying only papers uploaded/attached to the active chat session with status badges (`Ready` / `Processing`) and one-click remove (`×`) buttons to detach papers from the current chat scope.
    - `UploadModal.tsx` & `ChatWorkspace.tsx`: Passed `activeSessionId` directly into file uploaders so all uploads automatically bind to the active chat session; top header bar displays only active chat papers.
    - `page.tsx`: Immediately resets document list on chat switch or new chat creation so previous papers never flash into another chat session.
  - Automated verification:
    - Backend: 60 tests passing (`pytest -v`), 1 skipped, zero leaks across sessions.
    - Frontend TypeScript: `npx tsc --noEmit` exits with 0 errors.
    - Frontend ESLint: `npm run lint` exits with 0 errors and 0 warnings.

- **Feature 05: Research Chatbot Interface, GraphRAG Q&A Engine & Persistent Chat History**
  - Schema models (`backend/app/schemas/chat.py`): Defined `CitationItem`, `ChatMessageOut`, `ChatSessionSummary`, `ChatSessionDetail`, `CreateChatRequest`, `UpdateChatDocsRequest`, `SendMessageRequest`, and `SendMessageResponse`.
  - SQLite Chat Persistence (`backend/app/services/chat_store.py`):
    - Zero-dependency persistence using Python's built-in `sqlite3` stored at `backend/data/chats.db` with parent directory creation.
    - Tables `chat_sessions` and `chat_messages` with `FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE` and `PRAGMA foreign_keys = ON;`.
    - Implemented methods: `init_db()`, `create_session()`, `list_sessions()` (ordered by `updated_at DESC`), `get_session()`, `update_session_docs()`, `delete_session()`, and `append_message()` with automatic session titling from first user message.
  - Hybrid GraphRAG Q&A Engine (`backend/app/services/graphrag_qa_service.py`):
    - Retrieved local extracted JSON artifacts (summaries, entities, relationship evidence) scoped to attached `doc_ids` (or global knowledge base).
    - Queried Neo4j AuraDB 1-hop graph facts when configured, with graceful offline fallback.
    - Formatted grounded prompt with multi-turn conversation history (last 6 messages) and invoked local Ollama (`qwen2.5:3b`) at `POST /api/chat`.
    - Graceful offline fallback synthesizing structured responses directly from top matching graph entities and evidence quotes if Ollama times out or is offline.
  - REST Endpoints (`backend/app/routers/chat.py` & `backend/app/main.py`):
    - Registered `chat.router` exposing `GET /api/chats`, `POST /api/chats`, `GET /api/chats/{session_id}`, `PATCH /api/chats/{session_id}/documents`, `DELETE /api/chats/{session_id}`, and `POST /api/chats/{session_id}/messages`.
  - Test Isolation & Suite (`backend/tests/conftest.py` & `backend/tests/test_chat_router.py`):
    - Added autouse fixture isolating `upload_storage_dir`, `extracted_storage_dir`, `metadata_storage_path`, and `data_dir` into `tmp_path`, preventing live storage pollution and test-suite network hangs.
    - Created 10 comprehensive unit/integration tests for chat sessions, message persistence, Ollama synthesis, and offline fallback.
  - Frontend 2-Pane Research Chatbot UI:
    - `frontend/src/types/chat.ts`: TypeScript contracts for chats, messages, citations, and documents.
    - `frontend/src/lib/api.ts`: Typed API client for chat sessions, messages, and document management.
    - `frontend/src/components/ChatSidebar.tsx`: Left sidebar with **+ New Chat**, searchable conversation history with timestamps and delete buttons, and research papers section with scope checkboxes and quick upload trigger.
    - `frontend/src/components/ChatMessageBubble.tsx`: Formatted markdown responses with inline citations, code spans, blockquotes, and collapsible **Sources & Page Citations** pills with verbatim quote popovers.
    - `frontend/src/components/ChatWorkspace.tsx`: Context header with attached paper pills, welcome screen with 4 clickable starter research questions, animated thinking indicator, and auto-resizing composer bar with PDF attachment trigger.
    - `frontend/src/app/page.tsx`: Clean 2-pane layout integrating `ChatSidebar`, `ChatWorkspace`, and `UploadModal`, completely free of any entity-relationship graph canvas. Removed unused legacy graph components.
  - Automated verification:
    - Backend: 57 tests passing (`pytest -v`), 1 skipped. Live `backend/data/` completely unpolluted.
    - Frontend TypeScript: `npx tsc --noEmit` exits with 0 errors.
    - Frontend ESLint: `npm run lint` exits with 0 errors.

- **Feature 04: Complete Research Workspace & Interactive Knowledge Graph Explorer UI**
  - Schema models (`backend/app/schemas/graph.py`): Defined `GraphNode`, `GraphEdge`, `GraphSubgraphResponse`, and `DocumentItemResponse`.
  - Service extension (`backend/app/services/graph_persistence_service.py`): Implemented `get_subgraph(doc_id, limit)` supporting both per-document and global graph exploration with graceful offline fallback, and live status verification.
  - REST endpoints:
    - Added `GET /api/graph/subgraph` in `backend/app/routers/graph.py` accepting `doc_id` and `limit`.
    - Implemented `GET /api/documents` in `backend/app/routers/documents.py` returning all uploaded/extracted document metadata records sorted newest first with Neo4j sync tracking.
    - Added `DELETE /api/documents/{doc_id}` in `backend/app/routers/documents.py` to completely delete stored upload PDFs, extracted JSON artifacts, metadata records, and clean up associated Neo4j graph nodes and relationships.
    - Updated `GET /api/documents/{doc_id}/extraction` with `source_filename` support for direct artifact loading.
  - Frontend Workspace Architecture (`frontend/`):
    - Obsidian dark research theme (`#09090b` canvas, `#111114` panels, `#1f2028` borders, `#3b82f6` accent, custom sleek scrollbars).
    - 3-Pane Studio Shell:
      - `TopNavBar`: Fixed header with brand title, live Neo4j AuraDB status pill with periodic polling, KPI counters (Papers, Graph Entities, Relationships), and "+ Upload Paper" trigger.
      - `DocumentSidebar`: Collapsible research papers library with search, per-paper metadata (pages, entities, relationships), status pills (`Extracted`, `Neo4j Synced`), one-click Neo4j sync trigger, and inline paper deletion with confirmation prompt.
      - Center Main Stage with 3 switchable views:
        - `Knowledge Graph`: Zero-dependency interactive SVG canvas with custom force simulation, pan/zoom controls, draggable nodes, color-coded legend type filters, hover edge/neighbor highlights, and edge labels.
        - `Entities & Relationships`: Searchable and type-filterable tables with verbatim evidence quotes and page citation pills.
        - `Paper Summary & Insights`: Structured brief of selected paper or global knowledge base overview.
      - `InspectorPanel`: Right drawer providing detail inspection for clicked nodes/edges (canonical ID, type badge, description, source documents, connected relations with evidence) and conversational GraphRAG Q&A starter preview.
      - `UploadModal`: Seamless modal dialog wrapping the multi-PDF drag-and-drop uploader.
    - Typed API client (`frontend/src/lib/api.ts` & `frontend/lib/api.ts`) and TypeScript contracts (`frontend/src/types/workspace.ts` & `frontend/types/workspace.ts`).
  - Automated verification:
    - Backend: 47 unit and integration tests passing (`pytest -v`), 1 skipped (large batch constraint).
    - Frontend TypeScript: `npx tsc --noEmit` exits with 0 errors.
    - Frontend ESLint: `npm run lint` exits with 0 errors.

- **Feature 03: Neo4j Knowledge Graph Persistence & Provenance**
  - Schema models (`backend/app/schemas/graph.py`) defining `GraphHealthResponse` and `GraphSyncResult`.
  - Centralized Neo4j client (`backend/app/services/neo4j_client.py`) with `connection_timeout=8.0`, `max_connection_lifetime=300`, Windows `certifi` CA handling for `neo4j+s://`, and support for `neo4j+ssc://` cloud/self-signed handshakes.
  - Consolidated graph persistence service (`backend/app/services/graph_persistence_service.py`) supporting idempotent node merges with `canonical_id` unique constraints, label allowlist validation, edge clearing/upserts, and provenance tracking. Removed redundant `graph_service.py` duplicate.
  - Orchestrator integration (`backend/app/services/extraction_orchestrator.py`) invoking `GraphPersistenceService.persist_document_graph` when `neo4j_auto_sync=True` without blocking extraction on persistence failures.
  - REST endpoints (`backend/app/routers/graph.py`) exposing `GET /api/graph/health`, `POST /api/documents/{doc_id}/sync-graph`, and `GET /api/documents/{doc_id}/graph-status`.
  - Fixed environment path resolution in `backend/app/core/config.py` using `(str(BACKEND_ROOT / ".env"), ".env")` so `.env` loads correctly regardless of invocation directory.
  - Sanitized `backend/.env.example` to remove sensitive secrets while preserving documentation templates.
  - Automated tests passing: 43 unit and integration backend tests passing (`backend/.venv/Scripts/python.exe -m pytest -v`), with zero regressions across Feature 01–03.
  - Live verification: Successfully connected to Neo4j AuraDB (`4c93725c.databases.neo4j.io`), verified `GET /api/graph/health` returns `connected=True`, and persisted extracted document `d72e0eaf-a0dd-4e7d-aa4f-834155c05eeb` to Neo4j Aura (26 nodes and 21 relationships live in database).

- **Feature 01: Upload and Validate Research Papers**
  - Backend validation service (`backend/app/services/file_validator.py`) enforcing: `.pdf` extension, `%PDF-` header signature, `application/pdf` MIME type via `python-magic`, readability and encryption check via `pypdf`, 20 MB per-file limit.
  - Backend storage service (`backend/app/services/storage.py`) saving accepted PDFs to `backend/storage/uploads/` with UUID-based filenames, keeping in-memory metadata with original filenames.
  - Upload endpoint (`backend/app/routers/upload.py`) supporting batch uploads (up to 3 files, 60 MB total limit) with independent per-file validation and reporting.
  - Frontend upload service (`frontend/services/uploadService.ts`) and UI components (`UploadZone.tsx`, `FileList.tsx`, `UploadPanel.tsx`).
  - Unit and integration tests passing.

- **Feature 02: Local Multimodal Document Extraction & Graph-Ready Validation**
  - Schema contracts (`backend/app/schemas/extraction.py`) defining `EntityLabel` (6 academic labels), `RelationType` (7 academic types), `ExtractionJobStatus` (6 states), `RawChunkExtraction`, `DocumentStatusResponse`, and `DocumentExtractionResult`.
  - Centralized configuration (`backend/app/core/config.py`) anchoring storage directories (`STORAGE_BASE = BACKEND_ROOT / "storage"`) with automated path normalization so both Feature 01 and Feature 02 resolve identical directories regardless of current working directory, aligned on `OLLAMA_MODEL=qwen2.5:3b` and `OLLAMA_BASE_URL=http://localhost:11434`.
  - Document parser (`backend/app/services/document_parser.py`) implementing local layout-aware parsing, table/heading/page extraction, chunking, and lazy Docling loading with `DOCLING_PARSE_ERROR` handling.
  - Knowledge extractor (`backend/app/services/knowledge_extractor.py`) using local Ollama structured JSON extraction, `<UNTRUSTED_DOCUMENT_CONTENT>` prompt-injection delimiters, root `paper::{doc_id}` entity synthesis, canonical ID normalization (`^[a-z]+::.+$`), cross-chunk deduplication (provenance page merging, alias deduplication, longest description retention), and referential integrity (stripping self-loops and orphan edges with warnings).
  - Orchestrator (`backend/app/services/extraction_orchestrator.py`) managing atomic JSON writes to `backend/storage/metadata.json` and `backend/storage/extracted/{doc_id}.json` (`.tmp` replace) and status transitions (`queued -> parsing -> extracting -> completed/failed`) with safe error codes (`DOCLING_PARSE_ERROR`, `OLLAMA_TIMEOUT`, `OLLAMA_UNAVAILABLE`, `EXTRACTION_SCHEMA_INVALID`, `EXTRACTION_INTERNAL_ERROR`).
  - Router endpoints (`backend/app/routers/documents.py` and `backend/app/routers/upload.py`) triggering `BackgroundTasks` on accepted uploads and providing `GET /api/documents/{doc_id}/status`, `GET /api/documents/{doc_id}/extraction`, and `POST /api/documents/{doc_id}/extract`.
  - Frontend integration (`frontend/services/uploadService.ts`, `frontend/components/upload/DocumentExtractionStatus.tsx`, and `frontend/components/upload/FileList.tsx`) with strict TypeScript types, live status polling (`uploaded`/`queued`/`parsing`/`extracting`), terminal state handling (`completed`/`failed`), and dark-mode accessible retry button.
  - Automated tests passing: 39 unit/integration backend tests (`pytest -v`), clean TypeScript compilation (`npx tsc --noEmit`), and zero ESLint errors (`npm run lint`).
  - Live end-to-end verification: Successfully processed live 5-page research PDF (`IJRTI2304061.pdf`) via local Docling + Ollama (`qwen2.5:3b`), transitioning through `parsing` -> `extracting` -> `completed` and producing 25 entities and 21 relationships saved to `backend/storage/extracted/`.

## 4. Selected Technologies

| Area | Selection | Current status |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind CSS | Implemented & verified (Feature 05 2-Pane Research Chatbot UI) |
| Backend | Python + FastAPI | Implemented (Upload, Extraction, Graph persistence, Chat persistence, Subgraph/Chat APIs) |
| API communication | REST | Implemented for `/api/upload`, `/api/documents/*`, `/api/graph/*`, `/api/chats/*` |
| PDF validation | `pypdf` + `python-magic` | Implemented |
| File storage | Local private filesystem (`backend/storage/uploads/`, `backend/storage/extracted/`) | `uploads/` and `extracted/` implemented |
| Chat persistence | SQLite (`backend/data/chats.db`) | Implemented in `chat_store.py` (Feature 05) |
| Document parser | `Docling` (local) | Implemented in `document_parser.py` |
| Local extraction LLM | `Ollama` (`OLLAMA_MODEL` at `OLLAMA_BASE_URL`) | Implemented in `knowledge_extractor.py` and `graphrag_qa_service.py` |
| Background execution | FastAPI `BackgroundTasks` | Implemented in `upload.py` and `documents.py` |
| Graph database | Neo4j | Implemented & live-verified on AuraDB (Feature 03 & 04; GraphRAG backend in Feature 05) |
| Vector database | Qdrant | Selected; scheduled for future vector indexing |

## 5. Pending Decisions — Resolve When Relevant

- Embedding model and vector dimensions (for Qdrant feature).
- Cross-paper entity resolution / fuzzy alias merging strategy in Neo4j (Feature 03).
- Qdrant collection design, distance metric, and payload schema.
- Whether summaries are embedded as well as entities and relationships.
- Evidence-sufficiency policy and evaluation examples.
- Web-search provider and its data-retention/logging behavior.
- Exact privacy-safe query construction and allowlist policy.
- Authentication and access model, if required for future versions.
- Citation and source-location format.
- UI visual direction and design tokens (Dark Obsidian theme established for Studio).
- Deployment and hosting constraints.

## 6. Architecture Decisions

- **AD-001 — KB-first routing:** Search the private knowledge base before considering web fallback.
- **AD-002 — Neo4j graph:** Store explicit entities as nodes and relationships as edges.
- **AD-003 — Qdrant semantic index:** Store embeddings of approved entity/relationship representations.
- **AD-004 — Web fallback:** Use external search only when KB evidence is insufficient and the outbound query passes the privacy policy.
- **AD-005 — No paper leakage:** Uploaded papers and paper-derived private content must not be sent to web search.
- **AD-006 — Incremental stack selection:** Use Next.js, FastAPI, Neo4j, and Qdrant as selected technologies. Other providers and implementation details remain pending until needed.
- **AD-007 — Integration contribution:** The project integrates multimodal ingestion, graph storage, vector retrieval, evidence-based routing, privacy controls, and grounded answer generation; it does not claim a new graph algorithm or embedding model.
- **AD-008 — Independent file validation and private local storage:** Ingestion accepts up to 3 PDFs (≤20 MB each, ≤60 MB total) with per-file validation (extension, magic bytes, MIME type, PDF readability, password check) and persists accepted files to `backend/storage/uploads/` using UUID filenames.
- **AD-009 — 100% Local Document Extraction & Graph-Ready Boundary:** Document parsing (`Docling`) and structured extraction (`Ollama` at `OLLAMA_BASE_URL` using `OLLAMA_MODEL`) run strictly locally. Extractions enforce a fixed academic Neo4j ontology (`Paper`, `Concept`, `Method`, `Dataset`, `Metric`, `Author` and 7 typed edges), deterministic canonical IDs, and referential integrity checks before saving to `EXTRACTED_STORAGE_DIR` (`backend/storage/extracted/{doc_id}.json`).
- **AD-010 — 3-Pane Research Workspace & Lightweight Zero-Dependency SVG Graph Explorer:** Full viewport dark obsidian workspace layout (`h-screen overflow-hidden`) with top header (live Neo4j AuraDB health polling), left sidebar (collapsible document library with Neo4j sync triggers), center main stage, right inspector drawer, and dropzone upload modal.
- **AD-011 — 2-Pane Research Chatbot & Backend GraphRAG Engine:** Streamlined 2-pane research UI (`ChatSidebar` + `ChatWorkspace`) with inline citations and document scoping. SQLite for conversation persistence (`backend/data/chats.db`). Graph visualization canvas removed from frontend; Neo4j scoped strictly as backend GraphRAG retrieval engine. Isolated pytest runs using `tmp_path`.

- **AD-012 — Dual-Agent Orchestration & Privacy-Guarded Fallback:** Local Grounded Agent evaluates evidence sufficiency against scoped local papers and Neo4j graph facts. PrivacyGuard enforces fail-closed allowlisting and 4-gram n-gram redaction before delegating to Global Web Agent.
- **AD-013 — Markdown Session Export with Provenance:** Session export generates a reproducible, human-readable Markdown report containing session metadata, attached paper inventory, conversation turns, agent verification traces, verbatim paper citations with page numbers, and web references.

## 7. Next Up

1. **System Packaging & Final Delivery:**
   - Run end-to-end user verification for PDF ingestion, graph persistence, dual-agent chat, and session export.
   - Prepare presentation materials and demo scenarios.

## 8. Session Notes

- Completed Feature 08: Research Session Markdown Export & Final Production Documentation:
  1. Backend Markdown Export:
     - Implemented `GET /api/chats/{session_id}/export` in `backend/app/routers/chat.py` with filename resolution via `orchestrator.metadata_store` and memory metadata.
     - Added `get_session_with_messages(session_id)` helper in `ChatStore`.
     - Formats complete Markdown document with title, timestamps, attached papers, user/assistant dialogue, verification trace badge, local citations, and web links.
     - Returns `Response(content=markdown_text, media_type="text/markdown")` with `Content-Disposition` attachment header.
  2. Backend Verification Suite:
     - Added `test_export_chat_session_markdown` in `backend/tests/test_chat_router.py` verifying 404 behavior, status 200, Content-Type, Content-Disposition, and full Markdown body assertions.
  3. Frontend Export Trigger & Browser Download:
     - Added `exportChatMarkdown(sessionId)` API client method in `frontend/lib/api.ts`.
     - Added compact **Export .md** button in `frontend/components/ChatWorkspace.tsx` top header bar, active when a session has messages, triggering a dynamic browser file download (`research-session-<id>.md`).
  4. Production Documentation & Progress Tracking:
     - Rewrote `README.md` into a comprehensive submission guide with ASCII architecture diagrams, prerequisites, environment variables, run instructions, and test commands.
     - Updated `context/progress-tracker.md` marking Features 01–08 complete.
