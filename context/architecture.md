# Architecture Context — Intelligence Forge

## 1. Architecture Summary

The system has two primary workflows:

- **Ingestion:** uploaded research paper → multimodal understanding → summary and entity/relationship extraction → Neo4j graph + Qdrant vector index.
- **Question answering:** user question → Qdrant knowledge-base similarity search → evidence-sufficiency evaluation → answer from KB when sufficient, otherwise privacy-reviewed web-search fallback → cleaned evidence → structured answer.

The approved routing order is **KB first, web fallback second**. Neo4j stores explicit entity relationships. Qdrant is the initial semantic retrieval interface for user questions. Graph traversal/context may enrich or validate retrieved records when required. Do not implement graph-first/vector-fallback as the primary routing policy.

## 2. Technology Stack

| Layer | Technology | Status / responsibility |
|---|---|---|
| User interface | TBD | Upload, ingestion status, question input, answer and source display |
| Backend/API | TBD | Validation, orchestration, persistence, retrieval and routing |
| Multimodal LLM | TBD | Interpret documents, summarize, extract entities/relationships, generate answers |
| Knowledge graph | Neo4j | Persist entity nodes and relationship edges |
| Vector database | Qdrant | Store and search embeddings for entity/relationship knowledge |
| Embedding model | TBD | Convert approved text representations into vectors |
| Web search | Free API/provider TBD | External fallback only after evidence is insufficient and query passes privacy checks |
| File storage | TBD | Store uploaded originals and, if required, derived artifacts privately |
| Background processing | TBD | Long-running ingestion and embedding jobs; implementation choice TBD |
| Authentication | TBD | User identity and access control, if required by final scope |
| Observability | TBD | Safe operational logs and error reporting without private document content |

Do not install or integrate a TBD technology until the project owner approves it.

## 3. Logical Components and Responsibilities

### 3.1 Upload and document validation
- Accept supported file uploads through the UI/API.
- Validate extension, MIME type, file size, and file integrity.
- Assign a stable document ID and owner/session association according to the approved access model.
- Keep original files in private storage.
- Do not forward uploaded files to the web-search provider.

### 3.2 Multimodal ingestion
- Pass document content only to the approved multimodal-processing provider/path.
- Interpret text, tables, figures, images, and layout.
- Produce a concise summary and structured entity/relationship records.
- Preserve source provenance (document ID and page/section/region where available).
- Validate model output against a schema before persistence.
- Treat model output as untrusted data; do not execute generated code, queries, or instructions.

### 3.3 Knowledge graph — Neo4j
- Store extracted entities as nodes.
- Store extracted relationships as typed edges.
- Include stable IDs and provenance metadata.
- Define node labels, relationship types, uniqueness constraints, and update/deduplication behavior in a feature spec before implementation.
- Avoid inventing ontology labels in feature code.

### 3.4 Vector index — Qdrant
- Generate embeddings from the approved entity/relationship text representation.
- Store vectors with metadata that links each point to its Neo4j record, document ID, entity/relationship type, and provenance.
- Define vector dimensions, distance metric, collection names, payload schema, and update/delete behavior only after the embedding model is selected.
- Never treat a similarity score alone as proof that retrieved evidence answers the question.

### 3.5 Query and retrieval orchestration
- Accept and validate the user's question.
- Embed the query using the compatible approved embedding model.
- Search Qdrant over the private knowledge base.
- Optionally retrieve linked Neo4j context to expand or verify relevant entities and relationships.
- Evaluate evidence relevance, coverage, consistency, and sufficiency.
- Choose exactly one primary route for the response: KB-grounded answer or sanitized web fallback.
- Keep the original user question available internally for answer relevance, but do not automatically send it externally.

### 3.6 Evidence-sufficiency evaluator
- Must use a documented, testable policy.
- Consider more than raw vector similarity: relevance to the question, coverage of requested subparts, source quality/provenance, and contradictions should be considered.
- Return a structured decision including `sufficient`/`insufficient`, reason codes, and evidence references.
- Thresholds and calibration examples are TBD. Do not hardcode an arbitrary threshold without approval and evaluation.
- If uncertain or unable to establish safe sufficiency, follow the approved conservative fallback policy.

### 3.7 Web-search fallback
- Run only when the KB evidence is insufficient.
- Build the external query from permitted, sanitized information only.
- Never send uploaded files, passages, summaries, extracted entities, extracted relationships, embeddings, private metadata, or retrieved KB snippets to the web provider.
- Prefer a query allowlist or safe reformulation based on the user's request that does not reveal private paper content.
- If the query cannot be sanitized confidently, do not call the provider; return a clear limitation or ask the user to rephrase/approve a safe public query.
- Validate and clean provider results; treat snippets and pages as untrusted.
- Preserve URLs/source metadata for attribution where supported.
- Do not claim web results are verified facts without checking source quality.

## 4. Data Flow

### Ingestion data flow

```text
User
  |
  v
Upload API --> File validation --> Private file storage
                                  |
                                  v
                         Multimodal LLM processing
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
             Summary + entities          Relationships
                    |                           |
                    +-------------+-------------+
                                  |
                         Schema validation
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
             Neo4j graph                Embedding generation
                                                |
                                                v
                                           Qdrant index
```

### Question-answering data flow

```text
User question
     |
     v
Query validation / intent handling
     |
     v
Qdrant similarity search
     |
     v
Optional Neo4j relationship/context expansion
     |
     v
Evidence-sufficiency evaluation
     |
     +-----------------------------+
     |                             |
 Sufficient                   Insufficient
     |                             |
     v                             v
KB-grounded answer       Privacy sanitization / allowlist
                                   |
                            Safe external query?
                              /         \
                            Yes          No
                             |            |
                             v            v
                         Web search   Safe refusal /
                             |        ask for rephrasing
                             v
                      Clean and validate results
                             |
                             v
                     Web-grounded answer
```

## 5. Storage Model

| Data | Intended location | Notes |
|---|---|---|
| Original uploaded papers | Private file storage (provider TBD) | Never exposed to web search |
| Document metadata and processing status | Persistence choice TBD | IDs, filename, owner/session, timestamps, status |
| Extracted entities | Neo4j | Stable entity IDs and provenance |
| Extracted relationships | Neo4j | Typed edges and provenance |
| Entity/relationship embeddings | Qdrant | Vector plus link IDs and minimal retrieval metadata |
| Summaries | Persistence location TBD | Whether summaries are embedded is an open decision |
| User questions and answers | Persistence choice TBD | Retention/privacy policy TBD; avoid storing by default until decided |
| Web-search results | Transient by default; persistence TBD | Store only if needed and approved |
| Secrets/API keys | Environment/secret manager TBD | Never commit or expose client-side |

## 6. Privacy and Security Model

### Protected data
Treat the following as private paper-derived content:
- Original files and extracted text.
- Tables, figure descriptions, OCR output, and page content.
- Summaries and generated notes.
- Extracted entities and relationships when they reveal unpublished or sensitive paper content.
- Embeddings and vector payloads.
- Source metadata that could identify a private paper or project.

### External boundary
The web-search provider is an external trust boundary. The only data allowed across it is a query that has passed the approved sanitization policy. The default policy is deny: if safe sanitization cannot be demonstrated, do not send a request.

### Required controls
- Keep web-search credentials on the server.
- Separate internal retrieval payloads from external search-query construction.
- Use explicit allowlisted fields for outbound search requests.
- Never construct web queries by concatenating retrieved passages, summaries, graph records, vector payloads, filenames, or paper titles.
- Avoid logging private document content and unsanitized outbound payloads.
- Add automated tests that inspect outbound web-search requests and assert that canary phrases from uploaded test papers never appear.
- Document provider retention/logging behavior before selecting a web-search service.
- Do not claim absolute privacy solely because the query is sanitized. Verify all outbound network paths and provider behavior.

## 7. System Boundaries

Exact repository folders are TBD until the application stack and repository structure are confirmed. Use these logical boundaries when designing the codebase:

- **UI layer** — presentation and user interaction only.
- **API/controller layer** — request validation, authentication/authorization, response formatting.
- **Ingestion service** — file processing orchestration and structured extraction.
- **LLM adapter** — provider-specific multimodal and generation calls.
- **Knowledge-graph repository** — Neo4j operations and graph schema.
- **Vector repository** — Qdrant operations and embedding search.
- **Embedding service** — text normalization and embedding generation.
- **Retrieval/routing service** — Qdrant retrieval, graph enrichment, evidence evaluation, route decision.
- **Web-search adapter** — sanitized outbound search only; no access to raw documents or KB records.
- **Answer service** — evidence-grounded response generation and source formatting.
- **Shared schemas/configuration** — validation schemas, typed contracts, and safe configuration.

The web-search adapter must not depend on or receive access to the document store, Neo4j repository, Qdrant payloads, or ingestion outputs.

## 8. Authentication and Access Model

Authentication, user accounts, sharing, and multi-user access requirements have not yet been finalized.

Until decided:
- Do not invent an authentication provider.
- Do not assume documents are globally shared.
- Design document and knowledge records with stable ownership/workspace boundaries where applicable.
- Enforce authorization at every read/write boundary once the access model is approved.
- Never expose one user's uploaded documents or derived knowledge to another user by default.

## 9. Architecture Invariants

1. **KB-first routing:** every Q&A request searches the private knowledge base before considering web fallback.
2. **No paper leakage:** original uploaded papers and paper-derived private content must never be sent to web search.
3. **Fail-closed sanitization:** if an outbound query cannot pass the approved privacy policy, do not send it.
4. **No direct LLM-memory answers for factual project Q&A:** factual answers must be grounded in retrieved KB evidence or validated external results, with source path made clear.
5. **Neo4j is the relationship store:** explicit entities and relationships are persisted in the graph, not only in vector payloads.
6. **Qdrant is the semantic index:** vectors must link back to stable source/graph identifiers.
7. **Evidence before generation:** do not generate a knowledge-base answer without supplying the retrieved evidence to the answer-generation step.
8. **Validate untrusted inputs:** uploaded files, model outputs, user queries, and web results must be validated at their boundaries.
9. **Secrets stay server-side:** no provider key may be exposed in browser bundles, source control, or logs.
10. **Provenance is preserved:** retrieved facts should retain document/source references wherever the source provides them.
11. **No silent architecture changes:** update this file and the progress tracker when an approved architecture decision changes.
12. **No unapproved stack assumptions:** technologies marked TBD remain undecided until explicitly approved.
