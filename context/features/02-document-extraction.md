# Feature 02 — Local Multimodal Document Extraction & Graph-Ready Validation

## 1. Purpose and Scope

Implement a 100% local, privacy-preserving document parsing and structured knowledge extraction pipeline for uploaded research papers.

- **In Scope:**
  - Local layout-aware PDF parsing (`Docling`) preserving reading order, tables, section headings, and page numbers.
  - Local LLM structured extraction (`Ollama` with Pydantic schema constraints) generating a document summary, typed entities, and typed relationships.
  - Neo4j-ready validation, deterministic canonical ID normalization, and referential integrity enforcement.
  - Asynchronous background execution via FastAPI `BackgroundTasks` triggered automatically upon upload (plus manual re-trigger support).
  - Persistence of validated extraction artifacts to private local storage (`backend/storage/extracted/{doc_id}.json`).
  - Status polling and extraction inspection REST endpoints + frontend status display in `FileList`.
- **Out of Scope (Deferred to Future Features):**
  - Direct Neo4j database connection and Cypher writes (Feature 03).
  - Embedding generation and Qdrant vector indexing (Feature 04).
  - Question answering, retrieval routing, or web fallback.

---

## 2. Privacy & Security Boundaries

- **Strict Local Processing:** All PDF parsing (`Docling`) and LLM inference (`Ollama` at `localhost`) must execute locally. No document text, tables, metadata, or extracted entities may leave the local machine.
- **Prompt Injection Defense:** Parsed document text and table markdown are untrusted data. Extraction prompts must wrap document content in explicit data delimiters and instruct the model to ignore any directives embedded inside the paper.
- **Storage Hygiene:** Extracted JSON files reside in `backend/storage/extracted/` (excluded from Git via `.gitignore`). Never log raw extracted text or full extraction payloads to stdout/application logs.

---

## 3. Approved Technology & Configuration

| Setting | Env Variable | Default / Example | Notes |
|---|---|---|---|
| Ollama Endpoint | `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama server |
| Extraction Model | `OLLAMA_EXTRACTION_MODEL` | `qwen2.5:7b` | Configurable; supports structured JSON output |
| Extraction Temperature | `OLLAMA_TEMPERATURE` | `0.0` | Deterministic extraction |
| Request Timeout (sec) | `OLLAMA_TIMEOUT_SECONDS` | `120` | Per-chunk / document timeout |
| Max Chunk Characters | `EXTRACTION_MAX_CHUNK_CHARS` | `6000` | Section-aware chunking cap |
| Extracted Storage Dir | `EXTRACTED_STORAGE_DIR` | `backend/storage/extracted` | Local JSON artifact directory |

---

## 4. Data Contracts & Neo4j-Ready Ontology

### 4.1 Allowed Node Labels (`EntityLabel` Enum)
Only the following PascalCase labels are valid for downstream Neo4j nodes:
- `Paper`
- `Concept`
- `Method`
- `Dataset`
- `Metric`
- `Author`

### 4.2 Allowed Relationship Types (`RelationType` Enum)
Only the following SCREAMING_SNAKE_CASE types are valid for downstream Neo4j edges:
- `MENTIONS`
- `USES_METHOD`
- `EVALUATED_ON`
- `MEASURES`
- `OUTPERFORMS`
- `RELATED_TO`
- `AUTHORED_BY`

### 4.3 Canonical ID Normalization & Synthesis
- **Canonical ID Pattern:** `^[a-z]+::.+$`
  - Rule: `<label_lower>::<normalized_name>`
  - Normalization: Lowercase, trimmed, internal consecutive whitespace collapsed to single space, trailing punctuation (`.,;:!?`) stripped.
- **Root Paper Node:** Every document extraction automatically synthesizes a root entity with canonical ID `paper::{doc_id}`, label `Paper`, name `original_filename`, and provenance pointing to page 1 (`section_heading="Document Root"`).
- **Cross-Chunk Deduplication:**
  - Entities with identical canonical IDs across different chunks are merged.
  - Page numbers from provenance are aggregated into a sorted, unique list.
  - Aliases are deduplicated, stripped of casing variations matching the primary name, and sorted.
  - The longest non-empty description across occurrences is retained.

### 4.4 Referential Integrity Enforcement
- **Self-Loop Removal:** Any relationship where `source_id == target_id` is stripped and recorded in the document's `warnings` list.
- **Orphan Edge Removal:** Any relationship whose `source_id` or `target_id` does not match an entity present in the merged entity set is dropped and recorded in `warnings`.
- **Deduplication:** Multiple identical relationships (`source_id--type--target_id`) are collapsed into a single edge.

---

## 5. Failure Modes and Stable Error Codes

| Error Code | Trigger Condition | Status Code / State |
|---|---|---|
| `DOCLING_PARSE_ERROR` | PDF missing, encrypted, unreadable, or Docling parse failure | extraction state `failed` |
| `OLLAMA_TIMEOUT` | Ollama HTTP request exceeds timeout | extraction state `failed` |
| `OLLAMA_UNAVAILABLE` | Ollama service unreachable or returns connection/HTTP error | extraction state `failed` |
| `EXTRACTION_SCHEMA_INVALID` | Model output does not conform to `RawChunkExtraction` JSON schema | extraction state `failed` |
| `EXTRACTION_INTERNAL_ERROR` | Unhandled exception during extraction pipeline | extraction state `failed` |
| `DOCUMENT_NOT_FOUND` | Queried `doc_id` not found in metadata or local storage | HTTP 404 |
| `EXTRACTION_NOT_READY` | Extraction queried before status is `completed` | HTTP 409 |
| `EXTRACTION_IN_PROGRESS` | Manual re-extraction triggered while job is running (`parsing` or `extracting`) | HTTP 409 |

---

## 6. Storage & Persistence Contracts

- **Metadata Store:** Document status and metadata stored in `backend/storage/metadata.json`. All updates use atomic temporary file writes (`.tmp` replaced).
- **Extracted Artifacts:** Fully validated extraction results persisted to `backend/storage/extracted/{doc_id}.json` using atomic temporary file writes.
- **Status Transitions:** `uploaded` -> `queued` -> `parsing` -> `extracting` -> `completed` / `failed`.

---

## 7. REST Endpoints Specification

1. **`POST /api/upload`**: Validates PDF batch, stores accepted files, queues document in metadata store, and registers background extraction task with FastAPI `BackgroundTasks`.
2. **`GET /api/documents/{doc_id}/status`**: Returns `DocumentStatusResponse` with extraction status, page/entity/relationship counts, or error code/message.
3. **`GET /api/documents/{doc_id}/extraction`**: Returns `DocumentExtractionResult` when status is `completed`; returns 409 if extraction is not ready; returns 404 if record is missing.
4. **`POST /api/documents/{doc_id}/extract`**: Triggers background re-extraction (returns 202 with `status: queued`); returns 409 if job is already in progress; returns 404 if document is not found.
