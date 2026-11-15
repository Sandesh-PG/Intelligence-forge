from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class EntityLabel(str, Enum):
    PAPER = "Paper"
    CONCEPT = "Concept"
    METHOD = "Method"
    DATASET = "Dataset"
    METRIC = "Metric"
    AUTHOR = "Author"


class RelationType(str, Enum):
    MENTIONS = "MENTIONS"
    USES_METHOD = "USES_METHOD"
    EVALUATED_ON = "EVALUATED_ON"
    MEASURES = "MEASURES"
    OUTPERFORMS = "OUTPERFORMS"
    RELATED_TO = "RELATED_TO"
    AUTHORED_BY = "AUTHORED_BY"


class ExtractionJobStatus(str, Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    FAILED = "failed"


class EntityProvenance(BaseModel):
    doc_id: str
    page_numbers: list[int] = Field(min_length=1)
    section_heading: str | None = None


class ExtractedEntity(BaseModel):
    canonical_id: str = Field(..., pattern=r"^[a-z]+::.+$")
    label: EntityLabel
    name: str = Field(..., min_length=1, max_length=200)
    aliases: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=500)
    provenance: list[EntityProvenance] = Field(min_length=1)


class ExtractedRelationship(BaseModel):
    relationship_id: str
    source_id: str
    target_id: str
    type: RelationType
    evidence: str = Field(..., min_length=1, max_length=500)
    doc_id: str
    page_number: int = Field(..., ge=1)


class DocumentExtractionResult(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    doc_id: str
    original_filename: str
    model_id: str
    page_count: int = Field(..., ge=1)
    summary: str = Field(..., min_length=20)
    entities: list[ExtractedEntity]
    relationships: list[ExtractedRelationship]
    warnings: list[str] = Field(default_factory=list)


class DocumentStatusResponse(BaseModel):
    doc_id: str
    original_filename: str
    status: ExtractionJobStatus
    page_count: int | None = None
    entity_count: int | None = None
    relationship_count: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    updated_at: datetime


# --- Internal Raw LLM Output Contracts (Before Canonical ID Normalization) ---

class RawLLMNode(BaseModel):
    label: EntityLabel
    name: str = Field(..., min_length=1, max_length=200)
    aliases: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=500)


class RawLLMEdge(BaseModel):
    source_label: EntityLabel
    source_name: str = Field(..., min_length=1, max_length=200)
    target_label: EntityLabel
    target_name: str = Field(..., min_length=1, max_length=200)
    type: RelationType
    evidence: str = Field(..., min_length=1, max_length=500)


class RawChunkExtraction(BaseModel):
    chunk_summary: str = Field(..., min_length=10)
    entities: list[RawLLMNode] = Field(default_factory=list)
    relationships: list[RawLLMEdge] = Field(default_factory=list)