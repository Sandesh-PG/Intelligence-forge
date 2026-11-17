# Feature 03: Neo4j Knowledge Graph Persistence

## 1. Purpose & Scope
Persist validated document extraction artifacts (`backend/storage/extracted/{doc_id}.json`, produced by Feature 02) into a Neo4j graph database using idempotent, cross-paper entity resolution and parameterized Cypher queries.

This feature bridges offline document extraction and downstream GraphRAG retrieval / interactive graph visualization (Features 04–05).

### Out of Scope
- Vector embeddings or semantic chunk indexing (handled in Feature 04).
- Hybrid retrieval / natural-language QA endpoints (handled in Feature 04).
- Interactive graph canvas visualization UI (handled in Feature 05).
- Automatic execution of package managers (`pip install`, `npm install`, etc.) — strictly governed by the **No Auto-Install Policy**.

---

## 2. Hard Constraints & Engineering Rules
1. **No Auto-Install Rule:** Never run `pip install`, `npm install`, or any installer commands. Declare `neo4j>=5.28.0` (or `>=6.0.0`) in `backend/requirements.txt` and output the exact manual install command for the user.
2. **Parameterized Cypher Only:** Never interpolate entity labels, relationship types, or property values via f-strings or string concatenation into Cypher queries.
   - Use static, allowlisted label/relationship dispatch or validated `apoc`-free parameterized queries (`UNWIND $rows AS row ...`).
   - Strictly enforce the allowlisted node labels (`Paper`, `Concept`, `Method`, `Dataset`, `Metric`, `Author`) and relationship types (`MENTIONS`, `USES_METHOD`, `EVALUATED_ON`, `MEASURES`, `OUTPERFORMS`, `RELATED_TO`, `AUTHORED_BY`).
3. **Instance Agnostic (AuraDB & Local Bolt):** Must support both Neo4j AuraDB Free (`neo4j+s://...`) and local Neo4j Desktop/Docker (`bolt://localhost:7687`) purely through environment configuration (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`).
4. **Idempotent & Retry-Safe Writes:** Re-syncing the same `doc_id` (via manual retry or background re-run) must never create duplicate nodes or duplicate edges.
5. **Graceful Degradation:** If Neo4j credentials are unconfigured or the Neo4j instance is unreachable, the document status must record a clear, structured error (`GRAPH_PERSIST_ERROR` / `GRAPH_UNAVAILABLE`) without corrupting `backend/storage/extracted/{doc_id}.json`.

---

## 3. Configuration & Environment Contract

### 3.1 `backend/app/core/config.py` & `backend/.env.example`
Add the following settings to `Settings` in `backend/app/core/config.py` and document them in `backend/.env.example`:

| Env Variable | Default | Description |
| :--- | :--- | :--- |
| `NEO4J_URI` | `""` | Bolt/Aura connection URI (e.g., `neo4j+s://xxxx.databases.neo4j.io` or `bolt://localhost:7687`) |
| `NEO4J_USERNAME` | `"neo4j"` | Database username |
| `NEO4J_PASSWORD` | `""` | Database password |
| `NEO4J_DATABASE` | `"neo4j"` | Target Neo4j database name |
| `NEO4J_AUTO_SYNC` | `true` | Automatically persist graph immediately after Feature 02 extraction completes |
| `NEO4J_TIMEOUT_SECONDS` | `30` | Connection & transaction timeout in seconds |

### 3.2 `backend/requirements.txt`
Add:
```text
neo4j>=5.28.0