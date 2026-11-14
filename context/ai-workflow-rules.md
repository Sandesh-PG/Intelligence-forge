# AI Workflow Rules — Intelligence Forge

These instructions apply to every AI coding agent working in this repository.

## 1. Development Approach

- Follow incremental, context-driven, spec-driven development.
- Treat `AGENTS.md` and the context files as the persistent project contract.
- Implement one approved feature unit at a time.
- Read the active feature specification before implementation.
- Inspect the existing codebase before proposing or making edits.
- Do not infer missing product behavior or make unapproved technology choices.
- The project team owns product and architecture decisions. The agent may propose options but must not silently approve them.

## 2. Session Start

At the beginning of a coding session:

1. Read `AGENTS.md`.
2. Read `context/project-overview.md`.
3. Read `context/architecture.md`.
4. Read `context/code-standards.md`.
5. Read `context/ai-workflow-rules.md`.
6. Read `context/progress-tracker.md`.
7. Read `context/ui-context.md` when the task affects the UI.
8. Read the active feature specification and any referenced contracts.
9. Inspect the relevant existing code before editing.

Briefly summarize the current state and intended scope before broad or cross-cutting changes.

## 3. Scope Control

- Work on one feature specification at a time.
- Do not implement unrelated features in the same task.
- Do not refactor unrelated code.
- Prefer small changes with clear verification outcomes.
- Do not add speculative dependencies, endpoints, database fields, or UI elements.
- Do not change existing behavior unless the active specification requires it.
- Split work that crosses independent system boundaries into ordered, verifiable units.

## 4. Missing or Ambiguous Requirements

- Do not silently choose a technology or behavior that is marked Pending or Deferred.
- Do not invent graph labels, relationship types, embedding dimensions, collection names, thresholds, provider behavior, or privacy rules.
- Record unresolved decisions in `context/progress-tracker.md` when they affect the current work.
- Ask a concise, specific question when a decision blocks safe implementation.
- If implementation cannot proceed safely, stop at that boundary rather than creating a guessed placeholder.
- Distinguish approved decisions from assumptions and proposals.

## 5. Privacy and Security

- Treat uploaded documents, extracted text, model output, user queries, and web results as untrusted input.
- Never send uploaded papers or paper-derived private content to a web-search provider.
- Never construct web queries by concatenating KB results, summaries, extracted entities/relationships, vector payloads, filenames, or document metadata.
- Use only the approved sanitization/allowlist policy for outbound search.
- If sanitization is uncertain or fails, fail closed: do not call web search.
- Do not log private document content, raw extraction output, secrets, or unsafe outbound payloads.
- Keep provider credentials server-side.
- Add or update tests whenever a change touches the external privacy boundary.
- Do not claim the system is private or secure merely because a sanitization function exists; verify the actual outbound data path.

## 6. Retrieval and Answering

- Preserve the approved KB-first routing sequence.
- Search Qdrant first for semantic knowledge-base retrieval.
- Use Neo4j relationship context as specified by the active feature design.
- Evaluate evidence sufficiency before deciding to answer from the KB.
- Do not treat raw similarity as sufficient evidence without an approved policy.
- Use web fallback only after insufficient evidence and successful privacy checks.
- Distinguish KB evidence from web evidence in the response.
- Do not fabricate citations or source details.
- Constrain answer generation to the evidence selected for the chosen route.

## 7. Protected Areas

Do not modify without explicit approval or a requirement in the active specification:

- Environment files containing secrets or deployment credentials.
- Database schemas, graph ontology, Qdrant collection definitions, or migrations outside the active spec.
- Generated client code or generated UI-library internals.
- Lockfiles or package manifests except when a feature requires a dependency change.
- Existing prompts or model configuration used by another feature.
- CI/CD, deployment, or infrastructure configuration outside the active task.

## 8. Dependencies and Configuration

- Add dependencies only when the active feature requires them.
- Explain why each new dependency is needed.
- Prefer maintained, minimal dependencies.
- Do not hardcode provider keys, endpoints, model IDs, dimensions, or thresholds.
- Validate required environment variables at startup or integration initialization.
- Update a safe `.env.example` when configuration is added; never put real secrets there.

## 9. Documentation and Progress

After a meaningful change:
- Update `context/progress-tracker.md`.
- Update `context/architecture.md` when an approved architecture decision or actual system boundary changes.
- Update `context/code-standards.md` when a repository convention is established.
- Update `context/ui-context.md` when a visual decision is approved.
- Update the active feature specification if implementation details change without changing approved behavior.
- Record deviations and explain why they were necessary.

Never mark work complete merely because code was written.

## 10. Verification Before Closing a Feature

Run checks applicable to the repository and active specification:

1. Formatting and lint checks.
2. Type checks or static analysis.
3. Unit tests.
4. Relevant integration tests.
5. Privacy-boundary tests if external requests or document-derived data are involved.
6. Build/startup checks where available.
7. Manual verification of acceptance criteria.

Report exact commands and outcomes. If a check could not be run, state why. Do not fabricate successful verification.

## 11. Completion Report

When closing a feature, report:
- What was implemented.
- Important files changed.
- Tests/checks actually run and their results.
- Known limitations or deferred work.
- Whether context/spec/progress files were updated.
- The next recommended feature unit.

Then update `context/progress-tracker.md`.
