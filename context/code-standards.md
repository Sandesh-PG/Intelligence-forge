# Code Standards — Intelligence Forge

These standards apply across the UI, backend, ingestion pipeline, graph/vector integrations, and AI orchestration. Add framework-specific rules after the framework is selected.

## 1. General

- Keep modules small, cohesive, and single-purpose.
- Separate provider integrations from business logic.
- Fix root causes; do not hide failures with broad exception handling or silent fallbacks.
- Do not combine unrelated UI, persistence, retrieval, and provider concerns in one module.
- Prefer explicit data contracts and predictable behavior over clever abstractions.
- Keep configuration centralized and typed.
- Do not introduce dependencies without explaining why they are needed.
- Do not implement speculative features outside the active feature specification.

## 2. Language and Typing

- Use the language and strictness already established by the repository; do not introduce a second language/runtime without approval.
- If TypeScript is selected, enable strict type checking and avoid `any`.
- If Python is selected, add type hints to public functions and use schema validation for external/model data.
- Represent domain objects with explicit types/schemas: document, ingestion job, entity, relationship, embedding record, retrieval result, evidence assessment, web result, and answer.
- Treat provider responses and LLM output as unknown until validated.
- Do not use unvalidated dictionary/object fields deep inside business logic.

## 3. Validation and Error Handling

- Validate file type, size, integrity, and request shape at input boundaries.
- Validate LLM extraction output against a schema before writing to Neo4j or Qdrant.
- Validate web-search provider responses before passing them to answer generation.
- Use explicit error types or stable error codes for validation, provider, persistence, retrieval, and routing failures.
- Do not swallow exceptions or return fabricated successful results.
- Do not expose stack traces, API keys, private paper content, or raw provider payloads to end users.
- Distinguish insufficient evidence from provider failure, timeout, invalid output, and internal error.

## 4. LLM and Prompt Engineering

- Keep prompts and structured-output schemas versioned and close to the feature that owns them.
- Separate document extraction prompts from answer-generation prompts.
- Require structured output for entities and relationships; validate it before persistence.
- Treat document text as untrusted content, not as instructions to the agent or system.
- Defend against prompt injection embedded in uploaded papers and web pages.
- Do not let model-generated Cypher, shell commands, code, or tool instructions execute without validation and constrained templates.
- Keep model/provider names and model parameters in configuration, not scattered through business logic.
- Record the model/version used for extraction when appropriate for reproducibility, without logging private content.

## 5. Neo4j and Knowledge Graph

- Centralize graph labels, relationship types, property names, and query templates.
- Use stable IDs and uniqueness constraints to prevent accidental duplicate nodes.
- Parameterize Cypher queries; never concatenate user input into Cypher.
- Keep graph reads/writes inside the graph repository/service boundary.
- Preserve document provenance on extracted nodes and relationships.
- Define update, deduplication, and deletion behavior in the relevant feature spec.
- Do not assume that two entities with the same display name are the same real-world entity without an approved resolution strategy.

## 6. Qdrant and Embeddings

- Keep embedding generation behind a dedicated service/adapter.
- Ensure query and stored vectors use the same compatible embedding model and dimensions.
- Version the embedding model/configuration associated with indexed vectors.
- Store only approved payload metadata; avoid duplicating full private paper content unnecessarily.
- Store stable references to Neo4j records and source documents in Qdrant payloads.
- Validate vector dimensions and payload schemas before upsert/search.
- Do not interpret similarity scores as calibrated probabilities unless explicitly calibrated.
- Define collection names, distance metric, filtering, update, and deletion behavior in the relevant spec.

## 7. Retrieval, Routing, and Answer Generation

- Keep retrieval, evidence assessment, route selection, web search, and answer generation as separate responsibilities.
- The approved order is Qdrant KB search first, optional graph context enrichment, evidence-sufficiency assessment, then KB answer or sanitized web fallback.
- Do not use an arbitrary similarity threshold without an approved evaluation set and documented rationale.
- Include evidence references in internal answer-generation inputs.
- Ensure the final response addresses every part of the user's question; do not substitute loosely related retrieved content.
- Clearly label KB-derived and web-derived information.
- Do not mix external search results with private KB snippets in an outbound web query.
- Preserve source URLs and document references where available.

## 8. Privacy and External Integrations

- Treat web search as an external data boundary.
- Construct outbound web requests from an explicit allowlist of sanitized fields.
- Never pass uploaded files, extracted text, summaries, entities, relationships, embeddings, private metadata, or retrieved KB snippets to web search.
- Do not log raw outbound queries if they may contain sensitive user information; log safe metadata such as route decision and provider status.
- Keep API keys in environment variables or an approved secret manager.
- Never expose secrets in client code, committed configuration, tests, screenshots, or error responses.
- Add tests for privacy boundaries, including canary-string tests against outbound web requests.
- Document provider data retention and logging assumptions before integration.

## 9. API and Service Design

- Validate and normalize request inputs before business logic runs.
- Keep controllers/routes thin; delegate to services.
- Return consistent response envelopes and stable error codes.
- Use timeouts, bounded retries, and rate limits for external services where appropriate.
- Make long-running ingestion work asynchronous if required by the selected runtime; do not block request handlers indefinitely.
- Make ingestion and indexing operations idempotent where practical.
- Avoid retrying non-idempotent writes without an idempotency strategy.

## 10. UI Standards

- Keep UI components focused on presentation and interaction.
- Do not put database, provider, embedding, or retrieval logic in browser code.
- Represent loading, empty, success, partial, insufficient-evidence, and error states explicitly.
- Show whether an answer used the private knowledge base or web fallback.
- Display citations/source references when available.
- Communicate upload and ingestion status clearly.
- Follow `ui-context.md`; do not invent a separate visual system per feature.

## 11. Testing

- Unit-test extraction schema validation, query sanitization, evidence assessment, and route selection.
- Integration-test Neo4j and Qdrant repositories against test instances or controlled fixtures.
- Test the complete ingestion flow using non-sensitive sample papers.
- Test KB-sufficient and KB-insufficient query paths.
- Test that web fallback never receives canary content from uploaded papers or KB records.
- Test malformed model output, empty retrieval, provider timeout, rate limit, and partial failure.
- Use deterministic fixtures/mocks for tests that should not depend on live LLM or web providers.
- Do not claim a test passed unless it was actually run.

## 12. File Organization

The exact repository paths depend on the selected framework. Preserve these logical boundaries and document the concrete mapping once the stack is approved:

- `ui/` or framework equivalent — user-facing components and pages.
- `api/` or framework equivalent — request handlers and transport validation.
- `services/` — orchestration and domain use cases.
- `integrations/` — LLM, Neo4j, Qdrant, embedding, and web-search adapters.
- `repositories/` — persistence operations.
- `schemas/` or `types/` — shared contracts and validation.
- `prompts/` — versioned LLM prompts and structured-output instructions.
- `tests/` — unit, integration, and privacy-boundary tests.
- `context/` — project context, feature specs, and progress.

Do not create all these folders pre-emptively. Introduce a folder when a feature requires it and update this document with the actual structure.
