from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.graph import (
    GraphEdge,
    GraphHealthResponse,
    GraphNode,
    GraphSubgraphResponse,
    GraphSyncResult,
)

client = TestClient(app)


class TestGraphRouter:
    def test_graph_health_endpoint(self):
        with patch("app.services.neo4j_client.neo4j_driver.verify_connectivity") as mock_verify:
            mock_verify.return_value = GraphHealthResponse(
                connected=True,
                uri_configured=True,
                database="testdb",
                message="Successfully connected",
            )
            resp = client.get("/api/graph/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["connected"] is True
            assert data["uri_configured"] is True
            assert data["database"] == "testdb"

    def test_get_graph_subgraph_success(self):
        with patch("app.services.graph_persistence_service.GraphPersistenceService.get_subgraph") as mock_subgraph:
            mock_subgraph.return_value = GraphSubgraphResponse(
                nodes=[
                    GraphNode(
                        id="concept::attention",
                        label="Concept",
                        name="Attention",
                        description="Attention mechanism",
                        source_doc_ids=["doc-123"],
                    )
                ],
                edges=[
                    GraphEdge(
                        id="e1",
                        source="concept::attention",
                        target="method::transformer",
                        type="RELATED_TO",
                        evidence="Attention is used in transformers.",
                        doc_id="doc-123",
                    )
                ],
                total_nodes=1,
                total_edges=1,
            )
            resp = client.get("/api/graph/subgraph?doc_id=doc-123&limit=50")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_nodes"] == 1
            assert data["total_edges"] == 1
            assert data["nodes"][0]["id"] == "concept::attention"
            assert data["edges"][0]["type"] == "RELATED_TO"
            mock_subgraph.assert_called_once_with(doc_id="doc-123", limit=50)

    def test_sync_graph_missing_document_returns_404(self):
        resp = client.post("/api/documents/nonexistent-doc-id-000/sync-graph")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_sync_graph_success(self):
        with patch("app.services.graph_persistence_service.GraphPersistenceService.persist_document_graph") as mock_persist:
            mock_persist.return_value = GraphSyncResult(
                doc_id="test-doc-123",
                status="synced",
                nodes_upserted=5,
                relationships_created=3,
                neo4j_database="testdb",
            )
            resp = client.post("/api/documents/test-doc-123/sync-graph")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "synced"
            assert data["nodes_upserted"] == 5
            assert data["relationships_created"] == 3

    def test_get_graph_status_missing_document_returns_404(self):
        resp = client.get("/api/documents/nonexistent-doc-id-000/graph-status")
        assert resp.status_code == 404
