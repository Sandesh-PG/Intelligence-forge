# Feature 08: Research Session Markdown Export & Final Production Documentation

## 1. Execution Guardrails (NO TERMINAL COMMANDS — MANDATORY)
- **DO NOT RUN ANY TERMINAL OR SHELL COMMANDS:** Do NOT run `pytest`, `tsc`, `npm run lint`, `uvicorn`, `npm run dev`, or any shell command at all. All verification will be executed manually by the user after file creation.
- **NO AUTO-INSTALL:** Do NOT run `pip install` or `npm install`.

---

## 2. Backend File Manifest

### File 1: `backend/app/routers/chat.py` (Modify)
Add a clean Markdown export endpoint for any chat session:
- `@router.get("/{session_id}/export")`:
  - Fetches `session = chat_store.get_session_with_messages(session_id)` (raises `404` if not found).
  - Resolves attached paper filenames from `session.doc_ids` via `document_store` / extracted metadata.
  - Builds a clean, well-formatted Markdown report containing:
    - Report title (`# {session.title}`), timestamp, and **Attached Research Papers** list.
    - Every turn (`## User` / `## Intelligence Forge Assistant`), including:
      - Agent & Privacy verification summary (`Local Grounded`, `Web Fallback`, `Privacy Verified`).
      - **Local Paper Citations** (`- [Filename, p. X]: snippet`).
      - **External Web Sources** (`- [Title](URL)`).
  - Returns `Response(content=markdown_text, media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="research-session-{session_id[:8]}.md"'})`.

### File 2: `backend/tests/test_chat_router.py` (Modify)
- Add `test_export_chat_session_markdown` inside `TestChatRouterAPI` verifying `GET /api/chats/{session_id}/export` returns `200`, `text/markdown`, the session title, and message content, and returns `404` for a missing session.

---

## 3. Frontend File Manifest

### File 3: `frontend/lib/api.ts` (Modify)
- Add `exportChatMarkdown(sessionId: string): Promise<{ filename: string; content: string }>` calling `GET ${API_BASE_URL}/api/chats/${sessionId}/export`.

### File 4: `frontend/components/ChatWorkspace.tsx` (Modify)
- Add a compact **Export .md** button in the top chat header bar (next to the active paper badges / **+ Upload Paper** button, enabled whenever `activeSessionId` exists and `messages.length > 0`).
- Clicking **Export .md** fetches the Markdown report via `exportChatMarkdown(activeSessionId)` and triggers a browser file download (`research-session-<id>.md`).

---

## 4. Documentation & Progress Tracker Finalization

### File 5: `README.md` (Modify)
Update `README.md` so it serves as a complete, submission-ready project guide covering:
1. **Overview & Core Capabilities:** Local-first GraphRAG research assistant with Neo4j AuraDB vector + graph storage, session-scoped document isolation, Dual-Agent Orchestration (Local Grounded Agent + Global Web Search Agent), Zero-Leakage Privacy Firewall, and Markdown session export.
2. **System Architecture Diagram (ASCII):** Showing Frontend (`Next.js`), Backend (`FastAPI`), Ingestion (`Docling` + `Ollama` embeddings), Storage (`Neo4j AuraDB` + `SQLite`), and Dual-Agent + Privacy Firewall routing.
3. **Prerequisites & Environment Setup:** Python 3.11+, Node.js 18+, Ollama (`llama3.2` / `nomic-embed-text`), and Neo4j AuraDB credentials (`backend/.env`).
4. **Running the Application & Tests:** Exact commands for Backend (`uvicorn`), Frontend (`npm run dev`), `pytest`, `tsc`, and `lint`.

### File 6: `context/progress-tracker.md` (Modify)
Update `context/progress-tracker.md` to mark **Feature 08: Research Session Markdown Export & Final Production Documentation** as `Completed` alongside Features 01–07.