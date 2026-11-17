# Intelligence Forge

**A Multimodal Knowledge Retrieval & GraphRAG Research Assistant**

Intelligence Forge is an advanced, local-first research-assistance platform. It ingests academic papers (PDF), parses multi-modal layouts, extracts structured entities and relationships, and indexes them into **Neo4j AuraDB** and local storage. Answers are generated using a **Dual-Agent Orchestration Architecture** governed by a strict **Zero-Leakage Privacy Firewall**, guaranteeing that proprietary research remains protected while selectively augmenting responses with public web search when internal evidence is insufficient.

---

## 1. Overview & Core Capabilities

- **Local-First Multimodal Ingestion:** Validates PDFs via header signatures, MIME checks, and structural encryption scans (`pypdf` + `python-magic`), parsing layouts into structured chunks and tables using `Docling`.
- **Knowledge Graph & GraphRAG Persistence:** Extracts academic entities (`Paper`, `Concept`, `Method`, `Dataset`, `Metric`, `Author`) and typed relations, merging them idempotently into Neo4j AuraDB with deterministic canonical IDs and provenance tracking.
- **Session-Scoped Document Isolation:** Uploaded documents are strictly scoped to user chat sessions. Sessions query only attached papers, and deleting a session automatically cleans up unreferenced PDF binaries, extracted artifacts, and orphaned graph nodes.
- **Dual-Agent Orchestration:**
  - **Agent 1 (Local Grounded Agent):** Retrieves hybrid vector chunks and 1-hop Neo4j graph facts strictly scoped to active papers. Evaluates evidence sufficiency (`COVERAGE: COMPLETE` vs. `COVERAGE: INSUFFICIENT`).
  - **Agent 2 (Global Web Agent):** Triggered only when internal paper coverage is insufficient (or no papers are attached) and web search is enabled.
- **Zero-Leakage Privacy Firewall (`PrivacyGuard`):** Inspects candidate queries before external transmission. Redacts proprietary filenames, document IDs, and all 4-word verbatim paper n-grams to guarantee zero leakage of unpublished research.
- **Markdown Session Export:** One-click generation of comprehensive Markdown reports containing session metadata, attached research papers, message history, agent trace & privacy verifications, local paper citations, and external web sources.

---

## 2. System Architecture

```text
+-----------------------------------------------------------------------------------+
|                            Next.js 15+ Frontend (TypeScript)                     |
|  - 2-Pane Dark Obsidian Workspace (ChatSidebar + ChatWorkspace + UploadModal)    |
|  - Inline Citations, Verbatim Evidence Popovers & Markdown Session Export         |
+-----------------------------------------+-----------------------------------------+
                                          | REST API (HTTP)
+-----------------------------------------v-----------------------------------------+
|                              FastAPI Backend (Python 3.11+)                       |
|                                                                                   |
|  [Ingestion & Extraction Pipeline]                                                |
|  - Validation Service (pypdf + magic bytes check, <= 20 MB per PDF)               |
|  - Multimodal Document Parser (Docling layout extraction)                         |
|  - Academic Knowledge Extractor (Ollama qwen2.5:3b / llama3.2)                    |
|                                                                                   |
|  [Dual-Agent Orchestration Engine]                                                |
|  +-----------------------------------------------------------------------------+  |
|  | Agent 1: Local Grounded Agent                                               |  |
|  | - Hybrid Vector Chunks + Neo4j 1-Hop Graph Retrieval (Session-Scoped)       |  |
|  | - Evidence Sufficiency Evaluation (Coverage: COMPLETE vs INSUFFICIENT)      |  |
|  +--------------------------------------+--------------------------------------+  |
|                                         | Coverage Insufficient                   |
|  +--------------------------------------v--------------------------------------+  |
|  | Zero-Leakage Privacy Firewall (PrivacyGuard)                                |  |
|  | - Strips File Names, Document IDs & 4-Word Verbatim Paper N-Grams           |  |
|  | - Fail-Closed Allowlist Sanitization                                        |  |
|  +--------------------------------------+--------------------------------------+  |
|                                         | Sanitized Query                         |
|  +--------------------------------------v--------------------------------------+  |
|  | Agent 2: Global Web Agent (DuckDuckGo Search & Synthesis)                    |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------+-----------------------------------------+
                                          |
                +-------------------------+-------------------------+
                |                                                   |
+---------------v---------------+                   +---------------v---------------+
|        Neo4j AuraDB           |                   |         SQLite Database       |
| - Graph Nodes & Relationships |                   | - Session & Message Store     |
| - 1-Hop Fact Traversal        |                   | - Cascading Document Cleanup  |
| - Paper-Scoped Boundaries     |                   |   (backend/data/chats.db)     |
+-------------------------------+                   +-------------------------------+
```

---

## 3. Prerequisites & Environment Setup

### Prerequisites
- **Python:** 3.11 or higher
- **Node.js:** 18 or higher (with `npm`)
- **Ollama:** Installed and running locally
  ```bash
  ollama pull qwen2.5:3b
  ollama pull nomic-embed-text
  ```
- **Neo4j AuraDB:** Free or professional cloud instance (or local Neo4j 5.x)

### Environment Configuration
Create `backend/.env` (modeled after `backend/.env.example`):

```ini
# Neo4j AuraDB Connection
NEO4J_URI=neo4j+s://<your-aura-instance>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your-secure-password>
NEO4J_DATABASE=neo4j
NEO4J_AUTO_SYNC=true

# Ollama Local LLM & Embeddings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_EMBED_MODEL=nomic-embed-text

# Dual-Agent Orchestration & Privacy
ENABLE_GLOBAL_WEB_AGENT=true
```

Configure `frontend/.env.local` if custom backend URL is desired:
```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 4. Running the Application & Verification

### Running the Backend
From the repository root:
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
Interactive API documentation will be available at `http://localhost:8000/docs`.

### Running the Frontend
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to interact with the research chatbot workspace.

### Running Automated Tests & Verification
- **Backend Test Suite (Pytest):**
  ```bash
  pytest backend/tests/ -v
  ```
- **Frontend TypeScript Type Checking:**
  ```bash
  cd frontend
  npx tsc --noEmit
  ```
- **Frontend Code Quality & Linting:**
  ```bash
  cd frontend
  npm run lint
  ```

---

## 5. Security & Privacy Invariants

1. **Zero Raw Leakage:** Raw uploaded PDFs, extracted full text passages, and internal graph IDs are never passed to external search engines or third-party cloud services.
2. **N-Gram Redaction:** The Privacy Firewall computes word 4-grams across local document chunks and suppresses any search phrase that overlaps verbatim with uploaded text.
3. **Session Encapsulation:** Documents attached to Session A are invisible to Session B. All queries enforce explicit `doc_ids` boundaries across both vector indexes and Neo4j Cypher queries.
4. **Cascading Document Purge:** Deleting a chat session permanently scrubs unreferenced PDFs, parsed JSON artifacts, and associated Neo4j entities from the database.
