"""
Storage service for accepted PDF uploads.

Responsibilities:
- Write accepted PDF bytes to the private storage directory
  (backend/storage/uploads/) using a unique server-generated filename.
- Record in-memory document metadata (lost on process restart by design).
- Provide lookup of stored metadata by document ID.

The storage implementation is isolated so a different storage provider can
be introduced later without changing the router or validator.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.schemas.upload import DocumentMetadata, UploadStatus

logger = logging.getLogger(__name__)


def _ensure_storage_dir(destination_dir: Path | None = None) -> Path:
    """Create the storage directory if it does not exist and return its path."""
    target = destination_dir or settings.upload_storage_dir
    target.mkdir(parents=True, exist_ok=True)
    return target


# In-memory store: document_id -> DocumentMetadata
# Intentionally a module-level dict; data is lost on process restart.
_metadata_store: dict[str, DocumentMetadata] = {}


def store_pdf(
    original_filename: str,
    file_bytes: bytes,
    destination_dir: Path | None = None,
    session_id: str | None = None,
) -> DocumentMetadata:
    """
    Persist an accepted PDF to local storage and record its metadata.

    Args:
        original_filename: The client-provided filename (used only as metadata,
                           never as the stored filename).
        file_bytes: Validated PDF bytes ready to write.
        destination_dir: Directory where the PDF should be stored. Defaults
                         to settings.upload_storage_dir.
        session_id: Optional chat session ID the file was uploaded in.

    Returns:
        DocumentMetadata for the stored file.

    Raises:
        OSError: If the file cannot be written to disk.
    """
    storage_dir = _ensure_storage_dir(destination_dir)

    document_id = str(uuid.uuid4())
    # Stored filename is the document ID with a .pdf extension.
    # This prevents filename collisions and avoids exposing original names.
    stored_filename = f"{document_id}.pdf"
    destination = storage_dir / stored_filename

    destination.write_bytes(file_bytes)
    logger.info("Stored PDF as %s (%d bytes)", stored_filename, len(file_bytes))

    metadata = DocumentMetadata(
        document_id=document_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_size_bytes=len(file_bytes),
        upload_timestamp=datetime.now(tz=timezone.utc),
        status=UploadStatus.accepted,
        session_id=session_id,
    )
    _metadata_store[document_id] = metadata
    return metadata


def get_metadata(document_id: str) -> DocumentMetadata | None:
    """Return stored metadata for a document_id, or None if not found."""
    return _metadata_store.get(document_id)


def delete_metadata(document_id: str) -> bool:
    """Remove stored metadata for a document_id from the in-memory store."""
    if document_id in _metadata_store:
        del _metadata_store[document_id]
        return True
    return False


def list_metadata() -> list[DocumentMetadata]:
    """Return all in-memory metadata records."""
    return list(_metadata_store.values())

