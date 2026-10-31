# Progress Tracker — Intelligence Forge

Update this file after every meaningful implementation change and at the end of every AI coding session. Do not mark a feature complete until its acceptance criteria and required verification have passed.

## Current Phase

- **Phase:** Project context and architecture definition
- **Implementation status:** Not started / repository state not yet inspected
- **Current approach:** Context-driven, spec-driven incremental development

## Current Goal

- Finalize the project context documents and resolve the architecture decisions that block implementation.
- Then create the feature breakdown and detailed feature specifications before coding.

## Completed

- [x] Literature survey and research-gap analysis completed.
- [x] Guide-approved project objectives documented.
- [x] Current project overview and high-level data flow documented.
- [x] Initial AI-agent workflow, architecture, code standards, UI context, and progress tracker drafted.
- [x] Confirmed query routing direction: knowledge-base-first, sanitized web fallback.
- [ ] Inspect the actual application repository and map its existing structure.

## In Progress

- [ ] Review and approve the context files with the project team.
- [ ] Confirm current repository and existing implementation state.

## Next Up

1. Confirm application framework, backend framework, and current repository structure.
2. Select the multimodal LLM/provider and define its privacy/data-processing constraints.
3. Select embedding model and determine vector dimensions.
4. Define entity/relationship schema and Neo4j graph conventions.
5. Define Qdrant collection and payload design.
6. Select web-search provider and review its data retention/logging behavior.
7. Define query-sanitization policy and threat model.
8. Define evidence-sufficiency evaluation method and test examples.
9. Approve UI visual direction and design tokens.
10. Create `context/specs/00-build-plan.md` and detailed feature specifications under `context/features/`.

## Open Questions

- What is the existing frontend framework and version?
- What is the backend framework and runtime?
- Is authentication required for the first version? If yes, which provider?
- Where will original uploaded papers be stored?
- Which file formats and maximum upload sizes are supported?
- Which multimodal LLM will process documents, and will processing be local or hosted?
- Which embedding model will be used?
- Will summaries also be embedded, or only entities and relationships?
- What entity types and relationship types form the initial graph schema?
- How will entity deduplication and cross-paper entity resolution work?
- What Qdrant collection structure, distance metric, and payload schema will be used?
- Which free web-search API/provider will be used?
- What exact data may appear in a sanitized outbound query?
- How will sanitization be tested against paper-derived information leakage?
- How will evidence sufficiency be assessed and calibrated?
- What should happen if the web provider fails or the query cannot be safely sanitized?
- What UI theme, palette, typography, and component library does the team want?
- What are the deployment and hosting constraints/budget?

## Architecture Decisions

- **AD-001 — Knowledge-base-first routing:** Search the private knowledge base before considering external web search. Rationale: answers should use uploaded research first.
- **AD-002 — Neo4j for explicit relationships:** Store extracted entities as nodes and relationships as edges. Rationale: support relationship-centric and multi-hop research questions.
- **AD-003 — Qdrant for semantic retrieval:** Store embeddings of approved entity/relationship representations. Rationale: retrieve semantically relevant knowledge even when query wording differs.
- **AD-004 — Web search is fallback only:** Use external search only when KB evidence is insufficient. Rationale: prioritize private research knowledge and limit unnecessary external disclosure.
- **AD-005 — No uploaded-paper content in web requests:** Paper files and paper-derived private content must not be sent to web search. Outbound queries must pass an approved sanitization policy; fail closed when uncertain.
- **AD-006 — No unapproved technology assumptions:** LLM, embedding model, web provider, frameworks, thresholds, and sanitization implementation remain TBD until approved.
- **AD-007 — Integration is the project contribution:** The project integrates multimodal ingestion, graph storage, vector retrieval, evidence-based routing, privacy controls, and grounded answer generation; it does not claim a new graph algorithm or embedding model.

## Session Notes

- The previous literature report contains older wording describing graph-first retrieval with vector fallback. This is superseded by the current guide-approved objective: Qdrant/KB similarity search first, evidence-sufficiency check, then sanitized web fallback.
- The current project overview is based on the project owner's supplied context. No unconfirmed framework, provider, model, threshold, or UI theme has been invented.
- Update this section with repository findings, implementation details, blockers, and the exact next action at the end of each session.
