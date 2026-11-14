# Progress Tracker — Intelligence Forge

Update this file after meaningful implementation changes and at the end of each AI coding session. Do not mark a feature complete until its acceptance criteria and required verification have passed.

## 1. Current Project State

- **Development approach:** Incremental, spec-driven AI-agent workflow.
- **Repository:** Single Git repository initialized at the project root.
- **Frontend:** Next.js application with TypeScript and Tailwind CSS; UploadPanel, UploadZone, FileList, and uploadService implemented and verified.
- **Backend:** Python FastAPI backend with upload validation service, local storage service, and POST `/api/upload` endpoint implemented and verified.
- **Feature implementation:** Feature 01 (`01-upload-validate.md`) implemented and tested.
- **Databases:** Neo4j and Qdrant selected; setup and integration pending for subsequent ingestion features.

## 2. Current Goal

Feature 01 (`context/features/01-upload-validate.md`) — Research Paper Upload and Validation.

## 3. Completed

- **Feature 01: Upload and Validate Research Papers**
  - Backend validation service ([`file_validator.py`](file:///d:/7th_SEM/SKILL-LAB/project/Intelligence-forge/backend/app/services/file_validator.py)) enforcing: `.pdf` extension, `%PDF-` header signature, `application/pdf` MIME type via `python-magic`, readability and encryption check via `pypdf`, 20 MB per-file limit.
  - Backend storage service ([`storage.py`](file:///d:/7th_SEM/SKILL-LAB/project/Intelligence-forge/backend/app/services/storage.py)) saving accepted PDFs to `backend/storage/uploads/` with UUID-based filenames, keeping in-memory metadata with original filenames.
  - Upload endpoint ([`upload.py`](file:///d:/7th_SEM/SKILL-LAB/project/Intelligence-forge/backend/app/routers/upload.py)) supporting batch uploads (up to 3 files, 60 MB total limit) with independent per-file validation and reporting.
  - Frontend upload service ([`uploadService.ts`](file:///d:/7th_SEM/SKILL-LAB/project/Intelligence-forge/frontend/services/uploadService.ts)) and UI components ([`UploadZone.tsx`](file:///d:/7th_SEM/SKILL-LAB/project/Intelligence-forge/frontend/components/upload/UploadZone.tsx), [`FileList.tsx`](file:///d:/7th_SEM/SKILL-LAB/project/Intelligence-forge/frontend/components/upload/FileList.tsx), [`UploadPanel.tsx`](file:///d:/7th_SEM/SKILL-LAB/project/Intelligence-forge/frontend/components/upload/UploadPanel.tsx)).
  - Unit and integration tests ([`test_file_validator.py`](file:///d:/7th_SEM/SKILL-LAB/project/Intelligence-forge/backend/tests/test_file_validator.py), [`test_upload_router.py`](file:///d:/7th_SEM/SKILL-LAB/project/Intelligence-forge/backend/tests/test_upload_router.py)) passing with 17 passed checks.
  - Frontend typecheck (`npx tsc --noEmit`) and linting (`npm run lint`) clean with zero errors/warnings.

## 4. Selected Technologies

| Area | Selection | Current status |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind CSS | Initialized; upload UI implemented |
| Backend | Python + FastAPI | Initial app created; upload API implemented |
| API communication | REST | Implemented for `/api/upload` |
| PDF validation | `pypdf` + `python-magic` | Implemented |
| File storage | Local private filesystem (`backend/storage/uploads/`) | Implemented for Feature 01 |
| Graph database | Neo4j | Selected; setup/integration pending |
| Vector database | Qdrant | Selected; setup/integration pending |

## 5. Pending Decisions — Resolve When Relevant

- Multimodal model/provider and local or hosted processing path.
- Embedding model and vector dimensions.
- Initial graph ontology: entity types and relationship types.
- Entity deduplication and cross-paper entity resolution.
- Qdrant collection design, distance metric, and payload schema.
- Whether summaries are embedded as well as entities and relationships.
- Evidence-sufficiency policy and evaluation examples.
- Web-search provider and its data-retention/logging behavior.
- Exact privacy-safe query construction and allowlist policy.
- Persistent document metadata store (currently held in memory per Feature 01 spec).
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

## 7. Next Up

1. Decide and specify Feature 02 (e.g., document parsing / text and structure extraction).
2. Choose the multimodal document understanding model/strategy.
3. Define graph and vector schema for extracted content.

## 8. Session Notes

- Feature 01 completed strictly within spec boundaries: no PDF text extraction, LLM, Neo4j, or Qdrant was started.
- All per-file and batch constraints (3 files, 20 MB/file, 60 MB/batch) are verified on both backend and frontend.
- Backend pytest test suite has 17 passing tests.
- Frontend TypeScript type check and ESLint pass cleanly.
