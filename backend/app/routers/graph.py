from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.graph import GraphHealthResponse, GraphSyncResult, GraphSubgraphResponse
from app.services.graph_persistence_service import GraphPersistenceService
from app.services.neo4j_client import neo4j_driver

router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/graph/health", response_model=GraphHealthResponse)
async def graph_health():
    """Check Neo4j connectivity and configuration status."""
    return neo4j_driver.verify_connectivity()


@router.get("/graph/subgraph", response_model=GraphSubgraphResponse)
async def get_graph_subgraph(
    doc_id: Optional[str] = None,
    limit: int = Query(150, ge=1, le=1000),
):
    """Retrieve subgraph (nodes and edges) for a specific document or global graph."""
    return GraphPersistenceService.get_subgraph(doc_id=doc_id, limit=limit)


@router.post("/documents/{doc_id}/sync-graph", response_model=GraphSyncResult)
async def sync_document_graph(doc_id: str):
    """Manually trigger or retry Neo4j graph persistence for an extracted document."""
    try:
        result = GraphPersistenceService.persist_document_graph(doc_id)
        if result.status == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error_message or "Graph persistence failed",
            )
        return result
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extracted document artifact for {doc_id} not found",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Neo4j service error: {str(e)}",
        )


@router.get("/documents/{doc_id}/graph-status", response_model=GraphSyncResult)
async def get_document_graph_status(doc_id: str):
    """Get current Neo4j graph sync status for a document."""
    try:
        return GraphPersistenceService.get_graph_status(doc_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document record for {doc_id} not found",
        )