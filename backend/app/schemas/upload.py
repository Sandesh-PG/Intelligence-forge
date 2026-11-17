"""Pydantic schemas for the upload and validate feature (01-upload-validate)."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class UploadStatus(str, Enum):
    """Upload status for a single file result."""

    accepted = "accepted"
    rejected = "rejected"


class FileUploadResult(BaseModel):
    """Result for a single file in an upload batch."""

    original_filename: str
    document_id: Optional[str] = None
    status: UploadStatus
    rejection_reason: Optional[str] = None
    session_id: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """Response body for the POST /api/upload endpoint."""

    results: list[FileUploadResult]
    session_id: Optional[str] = None


class DocumentMetadata(BaseModel):
    """In-memory metadata for an accepted upload."""

    document_id: str
    original_filename: str
    stored_filename: str
    file_size_bytes: int
    upload_timestamp: datetime
    status: UploadStatus
    session_id: Optional[str] = None

