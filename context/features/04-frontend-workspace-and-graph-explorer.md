# Feature 04: Complete Research Workspace & Interactive Knowledge Graph Explorer UI

## 1. Execution Guardrails (Mandatory for AG)
- **NO BACKGROUND SERVERS:** Do NOT start `uvicorn` or `npm run dev`.
- **NO AUTO-INSTALL:** Do NOT run `npm install` or `pip install`. Build the interactive graph canvas using lightweight custom SVG + pan/zoom/force-layout physics in React/TypeScript (zero external graph library dependencies required).
- **STRICT FILE MANIFEST:** Create or modify every file listed below in exact order.

---

## 2. Backend Read Endpoints (Expose Neo4j & Document Lists to UI)

### File 1: `backend/app/schemas/graph.py` (Update)
Add response models for rendering nodes, edges, and document lists in the frontend:
- `GraphNode(BaseModel)`: `id: str` (`canonical_id`), `label: str` (primary type: `Paper | Concept | Method | Dataset | Metric | Author`), `name: str`, `description: str = ""`, `source_doc_ids: list[str] = []`
- `GraphEdge(BaseModel)`: `id: str`, `source: str`, `target: str`, `type: str`, `evidence: str = ""`, `page_number: Optional[int] = None`, `doc_id: str`
- `GraphSubgraphResponse(BaseModel)`: `nodes: list[GraphNode]`, `edges: list[GraphEdge]`, `total_nodes: int`, `total_edges: int`

### File 2: `backend/app/services/graph_persistence_service.py` (Update)
Add `@staticmethod def get_subgraph(doc_id: Optional[str] = None, limit: int = 150) -> GraphSubgraphResponse`:
- Queries Neo4j AuraDB via `neo4j_driver.get_driver()`.
- If `doc_id` is provided, matches `(n:Entity)` where `$doc_id IN n.source_doc_ids` and relationships `[r {doc_id: $doc_id}]` between them.
- Otherwise returns up to `limit` connected nodes and relationships across all synced papers.
- Gracefully returns empty `nodes=[]`, `edges=[]` if Neo4j is unconfigured or offline.

### File 3: `backend/app/routers/graph.py` (Update)
- Add `GET /api/graph/subgraph` accepting optional query params `doc_id: Optional[str] = None` and `limit: int = 150`, returning `GraphSubgraphResponse`.

### File 4: `backend/app/routers/documents.py` (Update)
- Ensure `GET /api/documents` returns a list of all uploaded/extracted document metadata records (`doc_id`, `filename`, `file_size`, `page_count`, `extraction_status`, `entity_count`, `relationship_count`, `summary`, `created_at`) sorted newest first by scanning `settings.extracted_storage_dir` and `settings.upload_storage_dir`.
- Ensure `GET /api/documents/{doc_id}/extraction` returns the full extracted JSON payload (`summary`, `entities`, `relationships`, `page_count`, `source_filename`) so the UI can render the Entities & Relationships Inspector.

---

## 3. Frontend Workspace Architecture (`frontend/`)

### Design System & Layout (`frontend/src/app/globals.css` & `layout.tsx`)
- **Theme:** Sleek dark obsidian research workspace (`#09090b` canvas, `#111114` elevated panels, `#1f2028` subtle 1px borders, `#3b82f6` electric blue primary accent, emerald/amber/violet semantic badges).
- **3-Pane Studio Shell (Full Viewport `h-screen overflow-hidden flex flex-col`):**
  1. **Top Header Bar (`h-14`):**
     - Brand title **Intelligence Forge** + subtle badge `GraphRAG Research Studio`.
     - Live **Neo4j AuraDB Status Pill** (polls `GET /api/graph/health` — green dot `AuraDB Connected (4c93725c)` or red dot `Disconnected`).
     - Global **+ Upload Paper** primary button (opens clean modal dropzone).
  2. **Left Sidebar (`w-72` collapsible):**
     - **Research Papers Library:** Lists all ingested documents from `GET /api/documents`.
     - Each document card shows filename, page count, entity/edge counts, and two compact status pills: `Extracted` + `Synced to Neo4j` (with a one-click `Sync` action button if not yet synced).
     - Clicking a paper selects it as the active workspace context (or `All Papers (Global Graph)` at the top).
  3. **Center Main Stage (`flex-1 flex flex-col min-w-0`):**
     - **View Switcher Tabs:**
       - `Knowledge Graph` (Interactive SVG force-directed / radial graph canvas)
       - `Entities & Relationships` (Searchable, type-filterable data tables with evidence quotes & page numbers)
       - `Paper Summary & Insights` (Clean structured brief of the selected paper)
     - **Interactive Graph Canvas (`KnowledgeGraphCanvas.tsx`):**
       - Color-coded legend bar (`Paper`, `Concept`, `Method`, `Dataset`, `Metric`, `Author`) with click-to-toggle type filters.
       - Zoom controls (`+`, `-`, `Reset View`), drag-to-pan canvas, and draggable nodes.
       - Hovering highlights connected edges and neighbor nodes; clicking any node or edge opens the **Node/Evidence Inspector Drawer** on the right.
  4. **Right Inspector / Assistant Drawer (`w-80`):**
     - **Inspector Mode (when a node/edge is clicked):** Shows entity canonical ID, type badge, description, source paper(s), and every relationship + verbatim evidence quote + page number.
     - **GraphRAG Q&A Preview Mode (default when nothing is selected):** Clean conversational panel displaying suggested research questions derived from the active graph nodes (e.g., *"Compare the methods evaluated in this paper"*), ready to connect to Feature 05's Q&A endpoint.

### Frontend File Manifest (`frontend/src/`)
1. `frontend/src/types/workspace.ts` — TypeScript interfaces matching backend responses (`DocumentItem`, `ExtractionDetail`, `GraphNode`, `GraphEdge`, `GraphSubgraphResponse`, `GraphHealthResponse`).
2. `frontend/src/lib/api.ts` — Typed API client functions (`fetchGraphHealth`, `fetchDocuments`, `fetchDocumentExtraction`, `fetchGraphSubgraph`, `syncDocumentGraph`, `uploadDocuments`).
3. `frontend/src/components/TopNavBar.tsx` — Header with live AuraDB health badge, KPI counters, and Upload modal trigger.
4. `frontend/src/components/DocumentSidebar.tsx` — Paper library list, selection state, and Neo4j sync status/trigger.
5. `frontend/src/components/KnowledgeGraphCanvas.tsx` — Interactive pan/zoom/drag SVG knowledge graph with entity-type color coding, legend filters, and edge labels.
6. `frontend/src/components/ExtractionTablesView.tsx` — Searchable & filterable Entities and Relationships tables with page citation pills.
7. `frontend/src/components/InspectorPanel.tsx` — Right-hand detail drawer for clicked graph nodes/edges + GraphRAG Q&A starter panel.
8. `frontend/src/components/UploadModal.tsx` — Polished modal wrapper around the multi-PDF drag-and-drop uploader so users can ingest additional papers anytime without losing their graph view.
9. `frontend/src/app/page.tsx` — Replaces the minimal single-dropzone page with the complete 3-pane Research Workspace (`TopNavBar` + `DocumentSidebar` + Center Tabs + `InspectorPanel`), seamlessly defaulting to the Upload Modal if zero papers exist yet.

---

## 4. Verification Criteria
1. `backend\.venv\Scripts\python.exe -m pytest -v` passes all existing and new `/api/graph/subgraph` & `/api/documents` tests.
2. `cd frontend && npx tsc --noEmit` exits with `0` TypeScript errors.
3. `cd frontend && npm run lint` exits with `0` ESLint errors.