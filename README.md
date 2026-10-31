# Intelligence Forge

**A Multimodal Knowledge Retrieval and Research Assistant**

Intelligence Forge is a research-assistance system that processes user-uploaded research papers, extracts structured knowledge, stores it in a Neo4j knowledge graph and Qdrant vector database, and answers user questions using a knowledge-base-first retrieval workflow. When the knowledge base does not contain sufficient evidence, the system may use a web-search fallback after applying the project's privacy and query-sanitization rules.

## Project goals

1. Extract entities and relationships from uploaded research papers and store them in Neo4j.
2. Generate embeddings for the extracted knowledge and store them in Qdrant.
3. Route questions based on evidence sufficiency: answer from the knowledge base when supported; otherwise use a sanitized web-search fallback.
4. Keep uploaded research-paper content private and prevent it from being sent to external search services.
5. Generate clear, structured answers that address the user's actual question and distinguish knowledge-base evidence from web-derived information.

## Repository documentation

```text
.
├── AGENTS.md
├── README.md
└── context/
    ├── project-overview.md
    ├── architecture.md
    ├── code-standards.md
    ├── ai-workflow-rules.md
    ├── ui-context.md
    ├── progress-tracker.md
    ├── features/
    │   └── README.md
    └── specs/
        └── 00-build-plan.md
```

## How AI coding agents must work

1. Read `AGENTS.md` before making changes.
2. Read all context files in the order specified there.
3. Read the relevant feature specification in `context/features/` before implementing a feature.
4. Implement only the approved scope of that feature.
5. Verify the implementation and update `context/progress-tracker.md`.
6. If a technical decision is not yet approved, do not silently choose one. Record it as an open question and ask the project team.

## Current status

The project definition and high-level architecture are documented. Several implementation choices remain intentionally unresolved, including the exact multimodal LLM, embedding model, web-search provider, evidence-sufficiency method, sanitization policy, application framework, and deployment environment. These must be decided before the affected implementation units begin.

## Important architecture rule

**Knowledge-base-first is the approved query flow.** Search the local project knowledge base first. If evidence is insufficient, consider web search using only a privacy-reviewed, sanitized query. Do not implement the older graph-first/vector-fallback design described in earlier literature-review drafts.
