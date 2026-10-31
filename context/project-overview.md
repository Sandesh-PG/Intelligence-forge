# Project Overview — Intelligence Forge

## 1. Overview

**Intelligence Forge: A Multimodal Knowledge Retrieval and Research Assistant** is a system for researchers who need to explore information distributed across multiple research papers and heterogeneous documents. A multimodal large language model processes uploaded papers, interprets text, tables, figures, and layout, generates concise summaries, and extracts important entities and relationships. The extracted knowledge is stored as a graph in Neo4j and represented as vectors in Qdrant. When a user asks a question, the system searches its private knowledge base first. If the retrieved evidence is sufficient, it generates a clear, structured answer grounded in that evidence. If evidence is insufficient, the system may search the public web using a sanitized query that does not disclose uploaded-paper content.

## 2. Problem Statement

Researchers work with many PDFs and other documents. Keyword search often misses semantic similarity, visual information, and relationships between concepts spread across papers. A plain LLM may answer from its pretrained knowledge and produce unsupported or hallucinated claims. At the same time, uploaded research papers may be private or unpublished and must not be disclosed to external search services.

## 3. Guide-Approved Objectives

1. **Construct a knowledge graph for research papers.** Extract entities and relationships from user-uploaded papers, store them as nodes and relationships in Neo4j, and convert the extracted entities and relationships into vector embeddings stored in Qdrant.
2. **Design a hybrid routing mechanism.** For each user query, perform similarity search over the knowledge base. If sufficient evidence is available, answer from the knowledge base in a clear format. Otherwise, perform web search through a selected free/search API, clean the returned data, and present a relevant answer.
3. **Design a secure approach for Q&A analysis.** Keep uploaded research-paper content from reaching the internet. Perform retrieval over the stored entity/relationship knowledge and sanitize every web-search query before it leaves the system. Ensure the final answer addresses the user's actual question.

## 4. Core User Flow

### Document ingestion

1. The user uploads one or more research papers.
2. The backend validates file type, size, and upload constraints.
3. The ingestion pipeline passes document content to the selected multimodal LLM through the approved private-processing path.
4. The model interprets relevant text, tables, figures, and layout.
5. The model produces a concise summary and structured entity/relationship extraction.
6. The system validates and normalizes the extracted structure.
7. Entities and relationships are stored in Neo4j with source-document provenance.
8. Embeddable representations of entities and relationships are generated and stored in Qdrant with identifiers that link back to their graph records and source documents.
9. The user can see ingestion status and whether processing succeeded or failed.

### Question answering

1. The user submits a question.
2. The system identifies the question intent and performs similarity retrieval against the private knowledge base in Qdrant; graph relationships in Neo4j may be used to enrich or validate the retrieved knowledge where required by the approved design.
3. The system evaluates whether the retrieved evidence is sufficiently relevant, complete, and specific to answer the question.
4. If evidence is sufficient, the answer-generation component creates a clear, structured response using the retrieved knowledge-base evidence.
5. If evidence is insufficient, the system prepares a privacy-reviewed, sanitized search query. It must not include uploaded files or paper-derived private content.
6. The selected web-search provider returns external results.
7. The backend validates, cleans, and normalizes those results.
8. The answer-generation component produces a response that matches the question and clearly distinguishes external web information from the user's private knowledge base.
9. The interface displays the answer and, where available, source references/citations.

## 5. Feature Categories

### A. Document and ingestion management
- Upload research papers.
- Validate supported file types and upload constraints.
- Track ingestion and processing status.
- Interpret document text, tables, figures, and layout using a multimodal LLM.
- Generate document summaries.
- Extract entities and relationships.
- Preserve provenance linking extracted knowledge to its source paper and location where available.

### B. Knowledge representation
- Store entities as Neo4j nodes.
- Store relationships as Neo4j edges.
- Generate embeddings for the approved entity/relationship representations.
- Store vectors and metadata in Qdrant.
- Maintain stable identifiers connecting Qdrant points to Neo4j records and source documents.

### C. Question answering and routing
- Accept natural-language questions.
- Search the knowledge base using vector similarity.
- Use graph context when required to understand relationships and multi-hop connections.
- Evaluate evidence sufficiency before selecting an answer path.
- Answer from the knowledge base when evidence is sufficient.
- Use sanitized web search only when knowledge-base evidence is insufficient.
- Clean external results and generate a structured answer relevant to the question.

### D. Privacy and security
- Keep uploaded papers and paper-derived private content out of web-search requests.
- Apply a defined query-sanitization policy before external search.
- Keep API credentials server-side.
- Validate uploaded files and external search results.
- Avoid logging document contents, extracted private content, secrets, or unsanitized search payloads.
- Make privacy behavior testable and auditable.

### E. User interface
- Provide a document upload and ingestion-status experience.
- Provide a research question-and-answer interface.
- Present structured answers and source attribution.
- Communicate whether an answer came from the knowledge base or external web search.
- Show useful loading, empty, error, and insufficient-evidence states.

## 6. Scope

### In Scope
- Research-paper upload and processing.
- Multimodal document understanding through a selected LLM.
- Summary, entity, and relationship extraction.
- Neo4j knowledge graph construction.
- Qdrant vector indexing for extracted entities and relationships.
- Knowledge-base-first similarity retrieval.
- Evidence-sufficiency evaluation and routing.
- Sanitized web-search fallback using a selected provider.
- Cleaning and grounding answers in retrieved evidence.
- Privacy controls and tests for preventing paper-content leakage.
- Interactive interface for ingestion and Q&A.
- Evaluation using representative research questions.

### Out of Scope Unless Explicitly Approved
- Training a new foundation model from scratch.
- Inventing a new embedding architecture or graph algorithm.
- Publicly sharing or indexing users' uploaded research papers.
- Sending full paper text, extracted passages, summaries, entities, relationships, or embeddings to web search.
- Automatic publication or redistribution of uploaded papers.
- Multi-user collaboration, paid subscriptions, or enterprise administration unless later added to scope.
- Claims of perfect hallucination elimination or absolute privacy without measurable evidence.

## 7. Evaluation Plan

Evaluate the integrated system with a curated set of questions covering:

1. **Direct fact lookup:** Can the system retrieve a specific fact present in an uploaded paper?
2. **Semantic similarity:** Can it find relevant information when the query uses different wording?
3. **Multi-hop entity relationships:** Can it connect related entities through Neo4j relationships?
4. **Cross-document synthesis:** Can it combine evidence from multiple uploaded papers without mixing up sources?
5. **Multimodal evidence:** Can it answer questions whose evidence is contained in a figure, table, or other visual document element?
6. **Routing correctness:** Does it answer from the KB when evidence is sufficient and use fallback when it is not?
7. **Privacy:** Do tests confirm that no uploaded-paper content or derived private data is sent in external web-search requests?
8. **Answer relevance and grounding:** Does the response answer the actual question and support claims with retrieved evidence?

## 8. Success Criteria

The project is successful when:

1. A user can upload a supported research paper and receive a successful/failed processing status.
2. The ingestion pipeline produces a summary and structured entities/relationships from supported document content.
3. Extracted entities and relationships are persisted in Neo4j and their approved vector representations are retrievable from Qdrant.
4. Qdrant retrieval returns relevant knowledge-base records for supported semantic questions.
5. The system can use Neo4j relationship context for multi-hop questions where needed.
6. Evidence-sufficiency logic selects the KB path when evidence is adequate and the fallback path when it is not.
7. The web-search request contains only an approved sanitized query and no uploaded-paper content or paper-derived private data.
8. External search results are cleaned and used to produce an answer relevant to the original user question.
9. Answers identify the source path and provide source references where the underlying source supports them.
10. The evaluation plan is executed and results, limitations, and failure cases are documented.

## 9. Current Product Decisions and Open Choices

The following are not finalized. Do not guess them during implementation:

- Multimodal LLM/provider and whether processing is local or through a hosted API.
- Supported document formats and upload size limits.
- Embedding model and vector dimensions.
- Exact entity/relationship schema and ontology.
- Whether summaries are also embedded, in addition to entities and relationships.
- Qdrant collection design and similarity metric.
- Evidence-sufficiency method, thresholds, and calibration dataset.
- Web-search provider/free API and its terms, logging, and retention behavior.
- Exact query-sanitization and allowlisting policy.
- Application framework, backend framework, authentication, file storage, deployment, and background-job technology.
- Citation and source-location format.
- UI visual direction and design tokens.

Record decisions in `architecture.md` and `progress-tracker.md` when approved.
