# AI Workflow Rules — Intelligence Forge

These are mandatory instructions for every AI coding agent working in this repository.

## 1. Overall Approach

- Follow context-driven, spec-driven, incremental development.
- Treat `AGENTS.md` and the context files as the persistent project contract.
- Build one approved feature unit at a time.
- Read the active feature specification before implementation.
- Do not infer missing product behavior or make unapproved technology choices.
- The human project team owns product and architecture decisions; the agent proposes options and implements approved decisions.

## 2. Mandatory Session Start

At the beginning of every coding session:

1. Read `AGENTS.md`.
2. Read `context/project-overview.md`.
3. Read `context/architecture.md`.
4. Read `context/ui-context.md`.
5. Read `context/code-standards.md`.
6. Read `context/ai-workflow-rules.md`.
7. Read `context/progress-tracker.md`.
8. Read the active feature specification and any referenced schemas.
9. Inspect the existing codebase before proposing edits; do not assume the repository is empty or matches documentation.

Summarize the current state and intended scope briefly before making broad or cross-cutting changes.

## 3. Scoping Rules

- Work on one feature specification at a time.
- Do not implement multiple unrelated features in one task.
- Do not refactor unrelated code while implementing a feature.
- Prefer small changes with clear verification outcomes.
- Do not add speculative abstractions, dependencies, endpoints, database fields, or UI elements.
- Do not change existing behavior unless the feature spec explicitly requires it.
- If a task crosses multiple system boundaries, split it into ordered units with explicit contracts.

## 4. When to Split Work

Split a task when it combines:
- UI work and ingestion/background-processing work.
- Neo4j schema changes and unrelated Qdrant behavior.
- Provider integration and unrelated interface redesign.
- Query sanitization and unrelated answer formatting.
- Multiple independent API endpoints or data migrations.
- Work that depends on an unresolved architecture choice.
- Changes that cannot be tested independently.

Keep tightly coupled work together only when splitting would leave no meaningful, verifiable intermediate result.

## 5. Handling Missing or Ambiguous Requirements

- Never silently choose a technology marked TBD.
- Never invent graph labels, relationship types, embedding dimensions, collection names, thresholds, provider behavior, or privacy rules.
- Record unresolved decisions in `context/progress-tracker.md`.
- Ask the project owner a concise, specific question when the decision blocks safe implementation.
- If a safe implementation cannot proceed, stop at the boundary; do not create a guessed placeholder implementation that appears complete.
- Distinguish assumptions from approved decisions in documentation and code comments.

## 6. Privacy and Security Rules

- Treat uploaded documents, extracted text, model output, user queries, and web results as untrusted input.
- Never send uploaded papers or paper-derived content to a web-search provider.
- Never create web queries by concatenating KB results, summaries, extracted entities/relationships, vector payloads, filenames, or document metadata.
- Use only the approved sanitization/allowlist policy for outbound search.
- If sanitization is uncertain or fails, fail closed: do not call web search.
- Do not log private document content, raw extraction output, secrets, or unsafe outbound payloads.
- Keep all provider credentials server-side.
- Add or update tests whenever a change touches the external privacy boundary.
- Do not describe the system as secure or private merely because a sanitization function exists; verify the actual outbound data path.

## 7. Retrieval and Answering Rules

- Preserve the approved KB-first routing sequence.
- Search Qdrant first for semantic knowledge-base retrieval.
- Use Neo4j relationship context as specified by the feature design; do not change the primary route order.
- Evaluate evidence sufficiency before deciding to answer from the KB.
- Do not treat raw similarity as sufficient evidence without the approved policy.
- Use web fallback only after an insufficient-evidence decision and successful privacy checks.
- Distinguish KB evidence from web evidence in the response.
- Do not fabricate citations or source details.
- Ensure answer generation is constrained to the evidence selected for the chosen route.

## 8. Protected Areas

Do not modify without explicit approval:
- Environment files containing secrets or deployment credentials.
- Database schemas, graph ontology, Qdrant collection definitions, or migrations outside the active spec.
- Generated client code or generated UI-library internals.
- Lockfiles or package manifests except when a feature spec requires a dependency change.
- Existing prompts or model configuration used by another feature.
- CI/CD, deployment, or infrastructure configuration outside the active task.

## 9. Dependencies and Configuration

- Add dependencies only when the active feature requires them.
- Explain why each new dependency is needed.
- Prefer maintained, minimal dependencies.
- Do not hardcode provider keys, endpoints, model IDs, dimensions, or thresholds.
- Validate required environment variables at startup or integration initialization.
- Update a safe `.env.example` when configuration is added; never put real secrets there.

## 10. Documentation and Progress

After a meaningful change:
- Update `context/progress-tracker.md`.
- Update `context/architecture.md` when an approved architecture decision or actual boundary changes.
- Update `context/code-standards.md` when a new repository convention is established.
- Update `context/ui-context.md` when a visual decision is approved.
- Update the active feature spec if implementation details change without changing the approved behavior.
- Record deviations and explain why they were necessary.

Never mark work complete merely because code was written.

## 11. Verification Before Closing a Feature

Run the checks applicable to the repository and active spec:

1. Formatting and lint checks.
2. Type checks or static analysis.
3. Unit tests.
4. Relevant integration tests.
5. Privacy-boundary tests if external requests or document-derived data are involved.
6. Build/startup check where available.
7. Manual verification of the feature's acceptance criteria.

Report exact commands and outcomes. If a check could not be run, state why. Do not fabricate successful verification.

## 12. Completion Response

When closing a feature, report:
- What was implemented.
- Important files changed.
- Tests/checks actually run and their results.
- Known limitations or deferred work.
- Whether context/spec/progress files were updated.
- The next recommended feature unit.

Then update `context/progress-tracker.md`.
