from typing import Optional
from pydantic import BaseModel, Field


class GraphHealthResponse(BaseModel):
    connected: bool
    uri_configured: bool
    database: str
    message: str


class GraphSyncResult(BaseModel):
    doc_id: str
    status: str  # "not_synced" | "persisting_graph" | "synced" | "failed"
    nodes_upserted: int = 0
    relationships_created: int = 0
    neo4j_database: str = "neo4j"
    synced_at: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class GraphNode(BaseModel):
    id: str  # canonical_id
    label: str  # primary type: Paper | Concept | Method | Dataset | Metric | Author
    name: str
    description: str = ""
    source_doc_ids: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    evidence: str = ""
    page_number: Optional[int] = None
    doc_id: str


class GraphSubgraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int
    total_edges: int


class DocumentItemResponse(BaseModel):
    doc_id: str
    filename: str
    file_size: int = 0
    page_count: int = 0
    extraction_status: str  # "uploaded" | "queued" | "parsing" | "extracting" | "completed" | "failed"
    entity_count: int = 0
    relationship_count: int = 0
    summary: str = ""
    created_at: str = ""
    synced_to_neo4j: bool = False
    session_id: Optional[str] = None



class GraphNode(BaseModel):
    id: str  # canonical_id
    label: str  # primary type: Paper | Concept | Method | Dataset | Metric | Author
    name: str
    description: str = ""
    source_doc_ids: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    evidence: str = ""
    page_number: Optional[int] = None
    doc_id: str


class GraphSubgraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int
    total_edges: int


class DocumentItemResponse(BaseModel):
    doc_id: str
    filename: str
    file_size: int = 0
    page_count: int = 0
    extraction_status: str  # "uploaded" | "queued" | "parsing" | "extracting" | "completed" | "failed"
    entity_count: int = 0
    relationship_count: int = 0
    summary: str = ""
    created_at: str = ""
    synced_to_neo4j: bool = False
    session_id: Optional[str] = None