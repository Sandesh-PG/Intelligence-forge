import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from app.core.config import settings
from app.schemas.graph import GraphSyncResult, GraphNode, GraphEdge, GraphSubgraphResponse
from app.services.neo4j_client import neo4j_driver
from app.services.embedding_service import EmbeddingService


class GraphPersistenceService:
    @staticmethod
    def _get_extracted_path(doc_id: str) -> Path:
        return settings.extracted_storage_dir / f"{doc_id}.json"

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 650, overlap: int = 100) -> list[str]:
        clean = (text or "").strip()
        if not clean:
            return []
        if len(clean) <= chunk_size:
            return [clean]
        chunks = []
        start = 0
        while start < len(clean):
            end = start + chunk_size
            chunk = clean[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += max(1, chunk_size - overlap)
        return chunks

    @staticmethod
    def persist_document_graph(doc_id: str) -> GraphSyncResult:
        path = GraphPersistenceService._get_extracted_path(doc_id)
        if not path.exists():
            raise FileNotFoundError(f"Extracted document artifact for {doc_id} not found")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        entities = data.get("entities", [])
        relationships = data.get("relationships", [])
        summary = data.get("summary", "")
        pages = data.get("pages", [])
        source_filename = data.get("source_filename") or data.get("original_filename") or f"{doc_id}.pdf"

        # If Neo4j is unconfigured, record not_synced
        if not settings.neo4j_uri:
            return GraphSyncResult(
                doc_id=doc_id,
                status="not_synced",
                nodes_upserted=0,
                relationships_created=0,
                neo4j_database=settings.neo4j_database,
                error_code="NEO4J_UNCONFIGURED",
                error_message="NEO4J_URI is not set in backend/.env",
            )

        try:
            driver = neo4j_driver.get_driver()
            now_iso = datetime.now(timezone.utc).isoformat()

            # 1. Prepare entity rows with vector embeddings
            node_rows = []
            paper_canonical = f"paper::{doc_id}"
            paper_emb = EmbeddingService.embed_text_sync(f"{source_filename}: {summary[:500]}")
            node_rows.append({
                "canonical_id": paper_canonical,
                "label": "Paper",
                "name": source_filename,
                "description": summary[:500] if summary else "",
                "aliases": [source_filename],
                "source_doc_ids": [doc_id],
                "doc_id": doc_id,
                "page_count": data.get("page_count", 0),
                "updated_at": now_iso,
                "embedding": paper_emb,
            })

            for e in entities:
                c_id = e.get("canonical_id")
                if not c_id or c_id == paper_canonical:
                    continue
                ent_name = e.get("name", c_id)
                ent_desc = e.get("description", "")
                ent_emb = EmbeddingService.embed_text_sync(f"{ent_name}: {ent_desc}")
                node_rows.append({
                    "canonical_id": c_id,
                    "label": e.get("label", "Concept"),
                    "name": ent_name,
                    "description": ent_desc,
                    "aliases": e.get("aliases", []),
                    "source_doc_ids": [doc_id],
                    "doc_id": doc_id,
                    "page_count": 0,
                    "updated_at": now_iso,
                    "embedding": ent_emb,
                })

            # 2. Prepare chunk rows from pages (or fallback to summary)
            chunk_rows = []
            if pages:
                for p in pages:
                    p_num = int(p.get("page_number", 1))
                    p_text = str(p.get("text", "")).strip()
                    if not p_text:
                        continue
                    p_chunks = GraphPersistenceService._chunk_text(p_text, chunk_size=650, overlap=100)
                    for c_idx, c_text in enumerate(p_chunks):
                        c_id = f"{doc_id}::p{p_num}::c{c_idx}"
                        c_emb = EmbeddingService.embed_text_sync(c_text)
                        chunk_rows.append({
                            "chunk_id": c_id,
                            "doc_id": doc_id,
                            "filename": source_filename,
                            "page_number": p_num,
                            "text": c_text,
                            "embedding": c_emb,
                        })
            elif summary:
                s_chunks = GraphPersistenceService._chunk_text(summary, chunk_size=650, overlap=100)
                for c_idx, c_text in enumerate(s_chunks):
                    c_id = f"{doc_id}::p1::c{c_idx}"
                    c_emb = EmbeddingService.embed_text_sync(c_text)
                    chunk_rows.append({
                        "chunk_id": c_id,
                        "doc_id": doc_id,
                        "filename": source_filename,
                        "page_number": 1,
                        "text": c_text,
                        "embedding": c_emb,
                    })

            with driver.session(database=settings.neo4j_database) as session:
                # 1. Ensure constraints / indexes
                session.run("CREATE CONSTRAINT entity_canonical_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.canonical_id IS UNIQUE")
                session.run("CREATE CONSTRAINT chunk_chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE")

                # 2. Upsert entity nodes
                safe_upsert_query = """
                UNWIND $rows AS row
                MERGE (n:Entity {canonical_id: row.canonical_id})
                SET n.name = CASE WHEN row.name IS NOT NULL AND row.name <> '' THEN row.name ELSE n.name END,
                    n.description = CASE WHEN row.description IS NOT NULL AND row.description <> '' THEN row.description ELSE n.description END,
                    n.updated_at = row.updated_at,
                    n.source_doc_ids = [x IN coalesce(n.source_doc_ids, []) + row.source_doc_ids WHERE x IS NOT NULL],
                    n.embedding = row.embedding
                """
                session.run(safe_upsert_query, rows=node_rows)

                # Add specific dynamic label additions based on allowlist
                for row in node_rows:
                    lbl = row["label"]
                    if lbl in ["Paper", "Concept", "Method", "Dataset", "Metric", "Author"]:
                        session.run(
                            f"MATCH (n:Entity {{canonical_id: $c_id}}) SET n:`{lbl}`",
                            c_id=row["canonical_id"]
                        )

                # 3. Clear existing chunks and relationships for this doc_id to ensure idempotency
                session.run("MATCH (c:Chunk {doc_id: $doc_id}) DETACH DELETE c", doc_id=doc_id)
                session.run("MATCH ()-[r {doc_id: $doc_id}]->() DELETE r", doc_id=doc_id)

                # 4. Upsert chunk nodes and link to root Paper node
                if chunk_rows:
                    upsert_chunks_query = """
                    UNWIND $chunks AS ch
                    MERGE (c:Chunk {chunk_id: ch.chunk_id})
                    SET c.doc_id = ch.doc_id,
                        c.filename = ch.filename,
                        c.page_number = ch.page_number,
                        c.text = ch.text,
                        c.embedding = ch.embedding
                    WITH c, ch
                    MATCH (p:Entity {canonical_id: $paper_id})
                    MERGE (p)-[:HAS_CHUNK]->(c)
                    """
                    session.run(upsert_chunks_query, chunks=chunk_rows, paper_id=paper_canonical)

                # 5. Create relationships
                edge_count = 0
                for rel in relationships:
                    src = rel.get("source_id")
                    tgt = rel.get("target_id")
                    rel_type = rel.get("type", "RELATED_TO").upper().strip()
                    if rel_type not in ["MENTIONS", "USES_METHOD", "EVALUATED_ON", "MEASURES", "OUTPERFORMS", "RELATED_TO", "AUTHORED_BY"]:
                        rel_type = "RELATED_TO"

                    if src and tgt:
                        query = f"""
                        MATCH (s:Entity {{canonical_id: $src}})
                        MATCH (t:Entity {{canonical_id: $tgt}})
                        MERGE (s)-[r:`{rel_type}` {{doc_id: $doc_id}}]->(t)
                        SET r.evidence = $evidence,
                            r.page_number = $page_number,
                            r.updated_at = $updated_at
                        """
                        session.run(
                            query,
                            src=src,
                            tgt=tgt,
                            doc_id=doc_id,
                            evidence=rel.get("evidence", ""),
                            page_number=rel.get("page_number"),
                            updated_at=now_iso
                        )
                        edge_count += 1

                return GraphSyncResult(
                    doc_id=doc_id,
                    status="synced",
                    nodes_upserted=len(node_rows) + len(chunk_rows),
                    relationships_created=edge_count,
                    neo4j_database=settings.neo4j_database,
                    synced_at=now_iso,
                )

        except Exception as e:
            return GraphSyncResult(
                doc_id=doc_id,
                status="failed",
                nodes_upserted=0,
                relationships_created=0,
                neo4j_database=settings.neo4j_database,
                error_code="NEO4J_EXECUTION_ERROR",
                error_message=str(e),
            )

    @staticmethod
    def get_graph_status(doc_id: str) -> GraphSyncResult:
        path = GraphPersistenceService._get_extracted_path(doc_id)
        if not path.exists():
            raise FileNotFoundError(f"Document record for {doc_id} not found")

        if not settings.neo4j_uri:
            return GraphSyncResult(
                doc_id=doc_id,
                status="not_synced",
                nodes_upserted=0,
                relationships_created=0,
                neo4j_database=settings.neo4j_database,
            )

        try:
            driver = neo4j_driver.get_driver()
            with driver.session(database=settings.neo4j_database) as session:
                res = session.run(
                    """
                    MATCH (n:Entity) WHERE $doc_id IN n.source_doc_ids
                    OPTIONAL MATCH ()-[r {doc_id: $doc_id}]->()
                    RETURN count(DISTINCT n) AS node_count, count(DISTINCT r) AS rel_count
                    """,
                    doc_id=doc_id,
                )
                rec = res.single()
                if rec and (rec["node_count"] > 0 or rec["rel_count"] > 0):
                    return GraphSyncResult(
                        doc_id=doc_id,
                        status="synced",
                        nodes_upserted=rec["node_count"],
                        relationships_created=rec["rel_count"],
                        neo4j_database=settings.neo4j_database,
                    )
        except Exception:
            pass

        return GraphSyncResult(
            doc_id=doc_id,
            status="not_synced",
            nodes_upserted=0,
            relationships_created=0,
            neo4j_database=settings.neo4j_database,
        )

    @staticmethod
    def delete_document_graph(doc_id: str) -> None:
        """
        Delete relationships and cleanup orphaned entity nodes associated with doc_id in Neo4j AuraDB.
        """
        if not settings.neo4j_uri:
            return

        try:
            driver = neo4j_driver.get_driver()
            with driver.session(database=settings.neo4j_database) as session:
                # 0. Delete all chunks associated with this doc_id
                session.run("MATCH (c:Chunk {doc_id: $doc_id}) DETACH DELETE c", doc_id=doc_id)

                # 1. Delete all relationships tagged with this doc_id
                session.run("MATCH ()-[r {doc_id: $doc_id}]->() DELETE r", doc_id=doc_id)

                # 2. Detach delete the root Paper node for this document
                session.run("MATCH (p:Entity {canonical_id: $paper_id}) DETACH DELETE p", paper_id=f"paper::{doc_id}")

                # 3. Update source_doc_ids on remaining entities
                session.run(
                    """
                    MATCH (n:Entity)
                    WHERE $doc_id IN n.source_doc_ids
                    SET n.source_doc_ids = [x IN n.source_doc_ids WHERE x <> $doc_id]
                    """,
                    doc_id=doc_id,
                )

                # 4. Remove any entities whose source_doc_ids is now empty
                session.run(
                    """
                    MATCH (n:Entity)
                    WHERE size(coalesce(n.source_doc_ids, [])) = 0
                    DETACH DELETE n
                    """
                )
        except Exception:
            pass

    @staticmethod
    def get_subgraph(doc_id: Optional[str] = None, limit: int = 150) -> GraphSubgraphResponse:
        """
        Queries Neo4j AuraDB via neo4j_driver.get_driver().
        If doc_id is provided, matches (n:Entity) where $doc_id IN n.source_doc_ids
        and relationships [r {doc_id: $doc_id}] between them.
        Otherwise returns up to limit connected nodes and relationships across all synced papers.
        Gracefully returns empty nodes=[], edges=[] if Neo4j is unconfigured or offline.
        """
        if not settings.neo4j_uri:
            return GraphSubgraphResponse(nodes=[], edges=[], total_nodes=0, total_edges=0)

        def pick_label(labels: list[str] | None) -> str:
            lbl_list = labels or []
            for candidate in ["Paper", "Concept", "Method", "Dataset", "Metric", "Author"]:
                if candidate in lbl_list:
                    return candidate
            return "Concept"

        try:
            driver = neo4j_driver.get_driver()
            nodes_map: dict[str, GraphNode] = {}
            edges_list: list[GraphEdge] = []

            with driver.session(database=settings.neo4j_database) as session:
                if doc_id:
                    # 1. Matched nodes for document
                    node_query = """
                    MATCH (n:Entity)
                    WHERE $doc_id IN n.source_doc_ids
                    RETURN n.canonical_id AS id,
                           labels(n) AS labels,
                           n.name AS name,
                           n.description AS description,
                           n.source_doc_ids AS source_doc_ids
                    LIMIT $limit
                    """
                    for rec in session.run(node_query, doc_id=doc_id, limit=limit):
                        c_id = rec["id"]
                        if not c_id:
                            continue
                        nodes_map[c_id] = GraphNode(
                            id=c_id,
                            label=pick_label(rec["labels"]),
                            name=rec["name"] or c_id,
                            description=rec["description"] or "",
                            source_doc_ids=rec["source_doc_ids"] or [],
                        )

                    # 2. Matched relationships for document
                    edge_query = """
                    MATCH (s:Entity)-[r]->(t:Entity)
                    WHERE r.doc_id = $doc_id
                    RETURN s.canonical_id AS source,
                           t.canonical_id AS target,
                           type(r) AS type,
                           r.evidence AS evidence,
                           r.page_number AS page_number,
                           r.doc_id AS doc_id
                    LIMIT $limit
                    """
                    for idx, rec in enumerate(session.run(edge_query, doc_id=doc_id, limit=limit)):
                        src = rec["source"]
                        tgt = rec["target"]
                        if not src or not tgt:
                            continue
                        edges_list.append(
                            GraphEdge(
                                id=f"e_{src}_{rec['type']}_{tgt}_{idx}",
                                source=src,
                                target=tgt,
                                type=rec["type"],
                                evidence=rec["evidence"] or "",
                                page_number=rec["page_number"],
                                doc_id=rec["doc_id"] or doc_id,
                            )
                        )
                else:
                    # Global graph: fetch relationships and attached nodes up to limit
                    edge_query = """
                    MATCH (s:Entity)-[r]->(t:Entity)
                    RETURN s.canonical_id AS source,
                           labels(s) AS source_labels,
                           s.name AS source_name,
                           s.description AS source_desc,
                           s.source_doc_ids AS source_docs,
                           t.canonical_id AS target,
                           labels(t) AS target_labels,
                           t.name AS target_name,
                           t.description AS target_desc,
                           t.source_doc_ids AS target_docs,
                           type(r) AS type,
                           r.evidence AS evidence,
                           r.page_number AS page_number,
                           r.doc_id AS doc_id
                    LIMIT $limit
                    """
                    for idx, rec in enumerate(session.run(edge_query, limit=limit)):
                        src = rec["source"]
                        tgt = rec["target"]
                        if not src or not tgt:
                            continue

                        if src not in nodes_map:
                            nodes_map[src] = GraphNode(
                                id=src,
                                label=pick_label(rec["source_labels"]),
                                name=rec["source_name"] or src,
                                description=rec["source_desc"] or "",
                                source_doc_ids=rec["source_docs"] or [],
                            )

                        if tgt not in nodes_map:
                            nodes_map[tgt] = GraphNode(
                                id=tgt,
                                label=pick_label(rec["target_labels"]),
                                name=rec["target_name"] or tgt,
                                description=rec["target_desc"] or "",
                                source_doc_ids=rec["target_docs"] or [],
                            )

                        edges_list.append(
                            GraphEdge(
                                id=f"e_{src}_{rec['type']}_{tgt}_{idx}",
                                source=src,
                                target=tgt,
                                type=rec["type"],
                                evidence=rec["evidence"] or "",
                                page_number=rec["page_number"],
                                doc_id=rec["doc_id"] or "",
                            )
                        )

                    # Supplement with standalone/unconnected nodes if capacity remains
                    if len(nodes_map) < limit:
                        remaining = limit - len(nodes_map)
                        node_query = """
                        MATCH (n:Entity)
                        RETURN n.canonical_id AS id,
                               labels(n) AS labels,
                               n.name AS name,
                               n.description AS description,
                               n.source_doc_ids AS source_doc_ids
                        LIMIT $remaining
                        """
                        for rec in session.run(node_query, remaining=remaining):
                            c_id = rec["id"]
                            if c_id and c_id not in nodes_map:
                                nodes_map[c_id] = GraphNode(
                                    id=c_id,
                                    label=pick_label(rec["labels"]),
                                    name=rec["name"] or c_id,
                                    description=rec["description"] or "",
                                    source_doc_ids=rec["source_doc_ids"] or [],
                                )

            nodes_list = list(nodes_map.values())
            return GraphSubgraphResponse(
                nodes=nodes_list,
                edges=edges_list,
                total_nodes=len(nodes_list),
                total_edges=len(edges_list),
            )
        except Exception:
            return GraphSubgraphResponse(nodes=[], edges=[], total_nodes=0, total_edges=0)

    @staticmethod
    async def retrieve_hybrid_context(question: str, doc_ids: list[str], top_k: int = 8) -> dict:
        """
        Hybrid Vector + Graph retrieval scoped strictly to doc_id IN doc_ids.
        Embeds question and retrieves top ranked :Chunk passages and top :Entity nodes + 1-hop relationships.
        Falls back to local extracted JSON files if Neo4j is offline or unconfigured.
        """
        if not doc_ids:
            return {"chunks": [], "entities": [], "relationships": [], "coverage": "NO_DOCS"}

        q_emb = await EmbeddingService.embed_text(question)
        q_words = set(re.findall(r"\w+", question.lower()))

        chunks_found: list[dict] = []
        entities_found: list[dict] = []
        relationships_found: list[dict] = []

        # 1. Try Neo4j retrieval first if configured
        if settings.neo4j_uri:
            try:
                driver = neo4j_driver.get_driver()
                with driver.session(database=settings.neo4j_database) as session:
                    # Chunks
                    chunk_res = session.run(
                        """
                        MATCH (c:Chunk)
                        WHERE c.doc_id IN $doc_ids
                        RETURN c.chunk_id AS chunk_id, c.doc_id AS doc_id, c.filename AS filename,
                               c.page_number AS page_number, c.text AS text, c.embedding AS embedding
                        """,
                        doc_ids=doc_ids,
                    )
                    for rec in chunk_res:
                        txt = rec["text"] or ""
                        emb = rec["embedding"] or []
                        sim = EmbeddingService.cosine_similarity(q_emb, emb) if emb else 0.0
                        txt_words = set(re.findall(r"\w+", txt.lower()))
                        kw_overlap = len(q_words.intersection(txt_words)) / max(len(q_words), 1)
                        total_score = round(sim + 0.15 * kw_overlap, 4)
                        chunks_found.append({
                            "chunk_id": rec["chunk_id"],
                            "doc_id": rec["doc_id"],
                            "filename": rec["filename"],
                            "page_number": rec["page_number"] or 1,
                            "text": txt,
                            "score": total_score,
                        })

                    # Entities
                    ent_res = session.run(
                        """
                        MATCH (n:Entity)
                        WHERE ANY(id IN coalesce(n.source_doc_ids, []) WHERE id IN $doc_ids) AND n.label <> 'Paper'
                        RETURN n.canonical_id AS id, n.name AS name, n.description AS description,
                               labels(n) AS labels, n.embedding AS embedding
                        """,
                        doc_ids=doc_ids,
                    )
                    for rec in ent_res:
                        name = rec["name"] or ""
                        desc = rec["description"] or ""
                        emb = rec["embedding"] or []
                        sim = EmbeddingService.cosine_similarity(q_emb, emb) if emb else 0.0
                        ent_words = set(re.findall(r"\w+", f"{name} {desc}".lower()))
                        kw_overlap = len(q_words.intersection(ent_words)) / max(len(q_words), 1)
                        total_score = round(sim + 0.2 * kw_overlap, 4)
                        entities_found.append({
                            "id": rec["id"],
                            "name": name,
                            "description": desc,
                            "labels": [lbl for lbl in (rec["labels"] or []) if lbl != "Entity"],
                            "score": total_score,
                        })

                    # 1-hop relationships for top entities
                    if entities_found:
                        top_entity_ids = [e["id"] for e in sorted(entities_found, key=lambda x: x["score"], reverse=True)[:6]]
                        rel_res = session.run(
                            """
                            MATCH (s:Entity)-[r]->(t:Entity)
                            WHERE r.doc_id IN $doc_ids AND (s.canonical_id IN $top_ids OR t.canonical_id IN $top_ids)
                            RETURN s.canonical_id AS source, t.canonical_id AS target, type(r) AS type,
                                   r.evidence AS evidence, r.page_number AS page_number, r.doc_id AS doc_id
                            LIMIT 25
                            """,
                            doc_ids=doc_ids,
                            top_ids=top_entity_ids,
                        )
                        for rec in rel_res:
                            relationships_found.append({
                                "source": rec["source"],
                                "target": rec["target"],
                                "type": rec["type"],
                                "evidence": rec["evidence"] or "",
                                "page_number": rec["page_number"] or 1,
                                "doc_id": rec["doc_id"],
                            })
            except Exception:
                pass

        # 2. Local JSON fallback if Neo4j returned no chunks or was offline
        if not chunks_found:
            for d_id in doc_ids:
                fpath = GraphPersistenceService._get_extracted_path(d_id)
                if not fpath.exists():
                    continue
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                    fname = data.get("source_filename") or data.get("original_filename") or f"{d_id}.pdf"
                    pages = data.get("pages", [])
                    if pages:
                        for p in pages:
                            p_num = int(p.get("page_number", 1))
                            p_text = str(p.get("text", "")).strip()
                            if not p_text:
                                continue
                            p_chunks = GraphPersistenceService._chunk_text(p_text, chunk_size=650, overlap=100)
                            for c_idx, c_text in enumerate(p_chunks):
                                c_emb = EmbeddingService.embed_text_sync(c_text)
                                sim = EmbeddingService.cosine_similarity(q_emb, c_emb)
                                txt_words = set(re.findall(r"\w+", c_text.lower()))
                                kw_overlap = len(q_words.intersection(txt_words)) / max(len(q_words), 1)
                                chunks_found.append({
                                    "chunk_id": f"{d_id}::p{p_num}::c{c_idx}",
                                    "doc_id": d_id,
                                    "filename": fname,
                                    "page_number": p_num,
                                    "text": c_text,
                                    "score": round(sim + 0.15 * kw_overlap, 4),
                                })
                    else:
                        summary = data.get("summary", "")
                        if summary:
                            s_chunks = GraphPersistenceService._chunk_text(summary, chunk_size=650, overlap=100)
                            for c_idx, c_text in enumerate(s_chunks):
                                c_emb = EmbeddingService.embed_text_sync(c_text)
                                sim = EmbeddingService.cosine_similarity(q_emb, c_emb)
                                txt_words = set(re.findall(r"\w+", c_text.lower()))
                                kw_overlap = len(q_words.intersection(txt_words)) / max(len(q_words), 1)
                                chunks_found.append({
                                    "chunk_id": f"{d_id}::p1::c{c_idx}",
                                    "doc_id": d_id,
                                    "filename": fname,
                                    "page_number": 1,
                                    "text": c_text,
                                    "score": round(sim + 0.15 * kw_overlap, 4),
                                })

                    if not entities_found:
                        for e in data.get("entities", []):
                            ent_name = e.get("name", "")
                            ent_desc = e.get("description", "")
                            ent_emb = EmbeddingService.embed_text_sync(f"{ent_name}: {ent_desc}")
                            sim = EmbeddingService.cosine_similarity(q_emb, ent_emb)
                            ent_words = set(re.findall(r"\w+", f"{ent_name} {ent_desc}".lower()))
                            kw_overlap = len(q_words.intersection(ent_words)) / max(len(q_words), 1)
                            entities_found.append({
                                "id": e.get("canonical_id"),
                                "name": ent_name,
                                "description": ent_desc,
                                "labels": [e.get("label", "Concept")],
                                "score": round(sim + 0.2 * kw_overlap, 4),
                            })

                    if not relationships_found:
                        for r in data.get("relationships", []):
                            relationships_found.append({
                                "source": r.get("source_id"),
                                "target": r.get("target_id"),
                                "type": r.get("type"),
                                "evidence": r.get("evidence", ""),
                                "page_number": r.get("page_number", 1),
                                "doc_id": d_id,
                            })
                except Exception:
                    pass

        # Sort and take top_k
        chunks_found.sort(key=lambda x: x["score"], reverse=True)
        entities_found.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = chunks_found[:top_k]
        top_entities = entities_found[:6]

        return {
            "chunks": top_chunks,
            "entities": top_entities,
            "relationships": relationships_found[:20],
        }