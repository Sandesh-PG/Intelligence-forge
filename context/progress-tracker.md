# Progress Tracker — Intelligence Forge

Update this file after meaningful implementation changes and at the end of each AI coding session. Do not mark a feature complete until its acceptance criteria and required verification have passed.

## 1. Current Project State

- **Development approach:** Incremental, spec-driven AI-agent workflow.
- **Repository:** Single Git repository initialized at the project root.
- **Frontend:** Next.js application with TypeScript and Tailwind CSS; UploadPanel, UploadZone, FileList, and uploadService implemented and verified.
- **Backend:** Python FastAPI backend with upload validation service, local storage service, local multimodal document extraction (`Docling` + `Ollama`), and document status/extraction REST APIs implemented and verified.
- **Feature implementation:**
  - Feature 01 (`01-upload-validate.md`) completed, verified (17 backend tests + clean TS/ESLint), and pushed.
  - Feature 02 (`02-document-extraction.md`) completed and verified end-to-end (39 backend tests passing, clean TS/ESLint, and live E2E extraction on a 5-page research paper producing 25 entities and 21 relationships).
- **Databases:** Neo4j and Qdrant selected; Neo4j persistence scheduled for Feature 03.

## 2. Current Goal

Feature 03 — Neo4j Knowledge Graph Persistence & Provenance (`context/features/03-graph-persistence.md` or next approved spec).

## 3. Completed

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
| Frontend | Next.js + TypeScript + Tailwind CSS | Initialized; upload UI implemented |
| Backend | Python + FastAPI | Initial app created; upload & extraction APIs implemented |
| API communication | REST | Implemented for `/api/upload` and `/api/documents/*` |
| PDF validation | `pypdf` + `python-magic` | Implemented |
| File storage | Local private filesystem (`backend/storage/uploads/`, `backend/storage/extracted/`) | `uploads/` and `extracted/` implemented |
| Document parser | `Docling` (local) | Implemented in `document_parser.py` |
| Local extraction LLM | `Ollama` (`OLLAMA_MODEL` at `OLLAMA_BASE_URL`) | Implemented in `knowledge_extractor.py` |
| Background execution | FastAPI `BackgroundTasks` | Implemented in `upload.py` and `documents.py` |
| Graph database | Neo4j | Selected; setup/integration scheduled for Feature 03 |
| Vector database | Qdrant | Selected; setup/integration pending |

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
- UI visual direction and design tokens.
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

## 7. Next Up

1. **Feature 03 — Neo4j Knowledge Graph Persistence & Provenance:**
   - Define Neo4j node constraints and unique indexes on canonical IDs (`label::name`).
   - Implement Neo4j driver connection and repository service in `backend/app/services/graph_service.py`.
   - Write parameterized Cypher statements to upsert entities (`Paper`, `Concept`, `Method`, `Dataset`, `Metric`, `Author`) and 7 typed relationships.
   - Maintain document-level and page-level provenance properties on graph nodes and edges.
   - Implement cross-paper entity deduplication and alias resolution.

## 8. Session Notes

- Resolved storage directory mismatch between Feature 01 and Feature 02 by anchoring `upload_storage_dir`, `extracted_storage_dir`, and `metadata_storage_path` in `backend/app/core/config.py` using `STORAGE_BASE = BACKEND_ROOT / "storage"`, with a Pydantic validator ensuring consistent absolute paths regardless of current working directory.
- Updated `backend/app/routers/upload.py` and `backend/app/services/storage.py` to use `settings.upload_storage_dir` directly.
- Restored `uploadDocuments` and missing types in `frontend/services/uploadService.ts` while preserving document extraction status methods with strict TypeScript types (zero `any`).
- Enhanced `DocumentExtractionStatus.tsx` Retry button styling for dark mode with `dark:border-zinc-600 dark:text-zinc-200 dark:hover:bg-zinc-800`.
- All automated checks passed: 39 pytest tests in `backend/`, clean TypeScript check (`npx tsc --noEmit`), and clean ESLint (`npm run lint`).
- Confirmed live local extraction on 5-page research PDF (`IJRTI2304061.pdf`) using Docling + Ollama `qwen2.5:3b`, outputting `Status: Completed — 25 entities, 21 relationships (5 pages)` and saving the validated graph-ready JSON artifact.
