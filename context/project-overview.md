# Project Overview — Intelligence Forge

## 1. Product Overview

**Intelligence Forge: A Multimodal Knowledge Retrieval and Research Assistant** helps researchers explore information distributed across research papers and other supported documents.

The system processes uploaded papers, extracts summaries, entities, and relationships, stores the structured knowledge in Neo4j, and stores vector representations in Qdrant. When a user asks a question, the system searches its private knowledge base first. If the available evidence is insufficient, it may use a privacy-reviewed web-search fallback.

## 2. Problem Statement

Researchers work with multiple papers containing text, tables, figures, and relationships between concepts. Keyword search can miss semantic similarity and connections across documents. General-purpose LLMs may also produce unsupported answers from pretrained knowledge.

Uploaded research papers may be private or unpublished. Their content and derived private information must not be disclosed to the external web-search provider.

## 3. Project Objectives

1. **Multimodal document understanding:** Process uploaded research papers and extract summaries, entities, and relationships.
2. **Knowledge graph construction:** Store entities as nodes and relationships as edges in Neo4j.
3. **Semantic knowledge retrieval:** Generate embeddings for approved entity/relationship representations and store them in Qdrant.
4. **Hybrid question answering:** Search the private knowledge base first; answer from it when evidence is sufficient, otherwise consider a privacy-safe web-search fallback.
5. **Grounded answers:** Generate responses relevant to the user's question and distinguish private-KB evidence from external web evidence.
6. **Privacy controls:** Prevent uploaded papers and paper-derived private content from reaching the web-search provider.

## 4. Core User Flows

### 4.1 Document ingestion

1. User uploads one or more research papers.
2. Backend validates the files.
3. An approved multimodal-processing path interprets document content, including text, tables, figures, and layout where supported.
4. The processing step produces a summary and structured entity/relationship data.
5. The backend validates and normalizes the extracted data.
6. Entities and relationships are persisted in Neo4j with source provenance.
7. An embedding model converts the approved entity/relationship representations into vectors.
8. Qdrant stores the vectors and the identifiers needed to link them to graph records and source documents.
9. The user can see processing status and whether ingestion succeeded or failed.

### 4.2 Question answering

1. User submits a natural-language question.
2. The system searches Qdrant for semantically relevant knowledge-base records.
3. Neo4j relationship context may enrich or validate retrieved records when required.
4. The system evaluates whether the retrieved evidence is relevant and sufficient for the question.
5. If sufficient, the answer is generated from the retrieved knowledge-base evidence.
6. If insufficient, the system may prepare a privacy-reviewed external query.
7. External results are validated and cleaned before answer generation.
8. The answer identifies whether it used the knowledge base or external web sources and includes source references where available.

## 5. Main Feature Areas

- Research-paper upload and validation.
- Document processing and ingestion status.
- Summary, entity, and relationship extraction.
- Neo4j graph persistence and provenance.
- Embedding generation and Qdrant indexing.
- Knowledge-base semantic retrieval.
- Neo4j relationship/context retrieval.
- Evidence-sufficiency evaluation and route selection.
- Privacy-reviewed web-search fallback.
- Evidence-grounded answer generation and source attribution.

## 6. Scope Boundaries

### In scope

The feature areas listed above, along with testing of ingestion, retrieval, routing, answer grounding, and privacy boundaries.

### Out of scope unless explicitly added

- Training a foundation model from scratch.
- Inventing a new embedding architecture or graph algorithm.
- Publicly sharing or indexing uploaded research papers.
- Sending paper content or paper-derived private data to web search.
- Automatic publication or redistribution of uploaded papers.
- Multi-user collaboration, paid subscriptions, or enterprise administration unless added to the agreed scope.

## 7. Evaluation Areas

The integrated system should be evaluated on:

1. Direct fact lookup from an uploaded paper.
2. Semantic retrieval when question wording differs from the source.
3. Multi-hop entity relationships using Neo4j.
4. Cross-document synthesis with source attribution.
5. Questions requiring evidence from figures or tables.
6. Correct KB-first routing and fallback decisions.
7. Privacy: no paper-derived private content in external search requests.
8. Answer relevance and grounding.

## 8. Approved Product and Technology Decisions

| Area | Decision | Status |
|---|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS | Decided; initialized |
| Backend | Python, FastAPI | Decided; environment and initial app created |
| Graph database | Neo4j | Selected; integration not yet implemented |
| Vector database | Qdrant | Selected; integration not yet implemented |
| Frontend/backend communication | REST API | Agreed |
| Repository | Single Git repository at project root | Configured |
| Development workflow | Incremental, spec-driven AI-agent implementation | Decided |
| Web-search provider | Not selected | Pending |
| Multimodal model and deployment | Not selected | Pending |
| Embedding model | Not selected | Pending |

## 9. Decisions to Make When Needed

The following are intentionally deferred until the relevant feature is designed:

- Multimodal model/provider and local or hosted deployment.
- Supported document formats and upload-size limits.
- Embedding model and vector dimensions.
- Entity types, relationship types, and entity-resolution rules.
- Qdrant collection design, distance metric, and payload schema.
- Whether summaries are embedded in addition to entities and relationships.
- Evidence-sufficiency policy and calibration examples.
- Web-search provider, provider data handling, and query-sanitization policy.
- File-storage approach.
- Authentication and access model.
- Citation and source-location format.
- Deployment and hosting approach.
- UI visual direction and design tokens.

Do not make these decisions silently during implementation. Record each decision when it becomes necessary and is approved.
