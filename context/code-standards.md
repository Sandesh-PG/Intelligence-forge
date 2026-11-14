# Code Standards — Intelligence Forge

These standards apply to the Next.js frontend, FastAPI backend, ingestion pipeline, graph/vector integrations, and AI orchestration.

## 1. General

- Keep modules small, cohesive, and single-purpose.
- Separate provider integrations from business logic.
- Fix root causes; do not hide failures with broad exception handling or silent fallbacks.
- Prefer explicit data contracts and predictable behavior.
- Keep configuration centralized.
- Do not introduce dependencies without explaining why they are needed.
- Do not implement work outside the active feature specification.
- Do not create speculative abstractions or folders before a feature requires them.

## 2. Frontend — Next.js and TypeScript

- Use the existing Next.js App Router structure.
- Use TypeScript for application code.
- Keep strict type checking enabled.
- Avoid `any`; use explicit types and safe narrowing.
- Keep UI components focused on presentation and interaction.
- Keep API communication in an appropriate service/client layer rather than scattering request logic through components.
- Do not put database, provider, embedding, or retrieval logic in browser code.
- Keep secrets and private provider credentials out of client-side code and browser bundles.
- Use accessible semantic elements, labels, keyboard interactions, and visible focus states.
- Represent loading, empty, success, partial, and error states explicitly.

## 3. Backend — Python and FastAPI

- Use the project's Python virtual environment for development.
- Add type hints to public functions and service boundaries.
- Use Pydantic schemas to validate API inputs, outputs, and untrusted model/provider data.
- Keep FastAPI route handlers thin; delegate business logic to services.
- Keep persistence operations inside repository/service boundaries.
- Use explicit error handling and stable error responses.
- Do not expose stack traces, secrets, private paper content, or raw provider payloads to users.
- Make long-running ingestion work asynchronous when required by the feature design; do not block request handlers indefinitely.

## 4. Validation and Error Handling

- Validate file type, size, integrity, and request shape at input boundaries.
- Validate LLM extraction output before writing to Neo4j or Qdrant.
- Validate web-search provider responses before passing them to answer generation.
- Distinguish insufficient evidence from provider failure, timeout, invalid output, and internal error.
- Do not swallow exceptions or return fabricated successful results.
- Use stable error codes where useful to clients and tests.

## 5. LLM and Prompt Engineering

- Keep prompts and structured-output schemas versioned and close to the feature that owns them.
- Separate document-extraction prompts from answer-generation prompts.
- Require structured output for entities and relationships; validate it before persistence.
- Treat document text and web pages as untrusted content, not as instructions to the system.
- Defend against prompt injection in uploaded papers and web content.
- Do not execute model-generated Cypher, shell commands, code, or tool instructions without validation and constrained templates.
- Keep model names and parameters in configuration rather than scattering them through business logic.
- Record model/version information when useful for reproducibility, without logging private content.

## 6. Neo4j and Knowledge Graph

- Centralize graph labels, relationship types, property names, and query templates.
- Use stable IDs and uniqueness constraints to prevent accidental duplicate nodes.
- Parameterize Cypher queries; never concatenate user input into Cypher.
- Keep graph reads/writes inside the graph repository/service boundary.
- Preserve document provenance on extracted nodes and relationships.
- Define update, deduplication, and deletion behavior in the relevant feature specification.
- Do not assume two entities with the same display name are identical without an approved resolution strategy.

## 7. Qdrant and Embeddings

- Keep embedding generation behind a dedicated service/adapter.
- Ensure stored vectors and query vectors use the same compatible embedding model and dimensions.
- Version the embedding model/configuration associated with indexed vectors.
- Store only approved payload metadata; avoid duplicating full private paper content unnecessarily.
- Store stable references to Neo4j records and source documents in Qdrant payloads.
- Validate vector dimensions and payload schemas before upsert/search.
- Do not interpret similarity scores as calibrated probabilities unless explicitly calibrated.
- Define collection, metric, filtering, update, and deletion behavior in the relevant feature specification.

## 8. Retrieval, Routing, and Answer Generation

- Keep retrieval, evidence assessment, route selection, web search, and answer generation as separate responsibilities.
- The approved order is Qdrant search first, optional Neo4j context enrichment, evidence assessment, then KB answer or sanitized web fallback.
- Do not use an arbitrary similarity threshold without an approved evaluation set and rationale.
- Include evidence references in internal answer-generation inputs.
- Ensure the final response addresses the user's actual question.
- Clearly distinguish KB-derived and web-derived information.
- Preserve source URLs and document references where available.

## 9. Privacy and External Integrations

- Treat web search as an external data boundary.
- Construct outbound web requests from explicitly approved, sanitized fields.
- Never pass uploaded files, extracted text, summaries, entities, relationships, embeddings, private metadata, or retrieved KB snippets to web search.
- Keep API keys in server-side environment variables or an approved secret manager.
- Do not log raw outbound queries if they may contain sensitive information.
- Add privacy-boundary tests, including canary-string tests against outbound requests.
- Document provider data-retention and logging assumptions before integration.

## 10. Testing and Verification

- Unit-test schema validation, query sanitization, evidence assessment, and route selection.
- Integration-test Neo4j and Qdrant repositories against test instances or controlled fixtures.
- Test ingestion with non-sensitive sample documents.
- Test KB-sufficient and KB-insufficient query paths.
- Test malformed model output, empty retrieval, provider timeout, rate limit, and partial failure.
- Use deterministic fixtures/mocks when tests should not depend on live model or web providers.
- Do not claim a test passed unless it was actually run.

## 11. Dependencies and Repository Structure

- Add dependencies only when the active feature requires them.
- Explain why each dependency is needed.
- Prefer maintained, minimal dependencies.
- Do not commit secrets, local databases, uploaded private papers, virtual environments, or generated build artifacts.
- Introduce folders when a feature needs them; do not create every possible layer in advance.
- Update this document when a repository convention is established.
