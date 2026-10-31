# Intelligence Forge — Build Plan

- Status: **Draft — dependency and stack decisions pending**
- This is an initial logical build sequence, not authorization to implement every unit immediately.
- Update this plan after inspecting the actual repository and approving the unresolved stack choices.

## Phase 0 — Project and technical foundations

| Unit | Name | Outcome | Dependencies |
|---|---|---|---|
| 00 | Repository audit and setup | Existing codebase, scripts, environment, and structure documented; baseline checks recorded | Repository access |
| 01 | Core configuration and contracts | Validated configuration and shared domain schemas established | Framework/runtime decision |
| 02 | Privacy threat model and outbound boundary | Sensitive-data inventory, allowed outbound fields, fail-closed behavior, and test strategy approved | Web provider and processing-provider review |

## Phase 1 — Document ingestion

| Unit | Name | Outcome | Dependencies |
|---|---|---|---|
| 03 | Document upload and validation | Supported files can be uploaded, validated, identified, and tracked | Storage and API decisions |
| 04 | Multimodal document processing | Selected multimodal LLM processes document content through the approved path | Unit 03; LLM decision |
| 05 | Summary and structured extraction | Schema-validated summary, entities, relationships, and provenance are produced | Unit 04; extraction schema |
| 06 | Neo4j persistence | Extracted entities and relationships are persisted with stable IDs and provenance | Unit 05; graph schema |
| 07 | Embedding generation and Qdrant indexing | Approved entity/relationship representations are embedded and indexed | Unit 05; embedding decision; Qdrant schema |

## Phase 2 — Knowledge-base question answering

| Unit | Name | Outcome | Dependencies |
|---|---|---|---|
| 08 | Query embedding and Qdrant retrieval | User questions retrieve relevant KB records | Unit 07 |
| 09 | Neo4j context enrichment | Retrieved records can be enriched with relevant graph relationships | Unit 06; Unit 08 |
| 10 | Evidence-sufficiency evaluator | A documented, testable decision indicates whether KB evidence can answer a question | Units 08–09; evaluation examples |
| 11 | KB-grounded answer generation | Sufficient KB evidence produces a structured, source-grounded answer | Unit 10; answer prompt/schema |

## Phase 3 — Secure web fallback

| Unit | Name | Outcome | Dependencies |
|---|---|---|---|
| 12 | Query sanitization policy and implementation | Outbound search queries are constructed from approved safe information only | Unit 02; sanitization decision |
| 13 | Web-search provider adapter | Sanitized queries can be sent to the selected provider and results validated | Unit 12; provider decision |
| 14 | Web-result cleaning and answer generation | Cleaned external results produce a relevant answer with source links | Unit 13 |
| 15 | End-to-end route orchestration | KB-first route selects KB answer or safe web fallback correctly | Units 10–14 |

## Phase 4 — User experience and evaluation

| Unit | Name | Outcome | Dependencies |
|---|---|---|---|
| 16 | Document management UI | Upload and ingestion status are usable and understandable | Units 03–05; UI decision |
| 17 | Research Q&A UI | User can ask questions and view structured answers and sources | Unit 15 |
| 18 | Privacy and routing test suite | Canary tests verify paper-derived content does not cross the web boundary | Units 02, 12–15 |
| 19 | Research-question evaluation | System is evaluated on fact lookup, semantic similarity, multi-hop, cross-document, and multimodal questions | Integrated system |
| 20 | Final hardening and documentation | Known limitations, setup, architecture, evaluation results, and demo flow are documented | Previous units |

## Ordering constraints

- Inspect the repository before creating or restructuring folders.
- Resolve privacy boundaries before implementing any external web-search integration.
- Define extraction schemas before persisting graph/vector records.
- Select the embedding model before creating Qdrant collections.
- Calibrate evidence sufficiency using representative questions; do not pick an arbitrary score threshold.
- Implement and test the sanitized query builder before enabling live web fallback.
- Build UI integration against stable API contracts.
- Reorder or merge units if repository inspection shows a better dependency graph.

## Definition of Done for every unit

- The unit matches its approved feature spec.
- Input/output contracts and error behavior are implemented.
- Relevant tests pass.
- Security/privacy checks pass when applicable.
- No unrelated files or behavior were changed.
- Documentation and `context/progress-tracker.md` are updated.
