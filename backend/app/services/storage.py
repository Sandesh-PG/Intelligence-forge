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

from app.schemas.upload import DocumentMetadata, UploadStatus

logger = logging.getLogger(__name__)

# Private storage directory — relative to the project root when the backend
# process is started from the repository root, or from the backend/ directory.
# The path is resolved at import time so the service fails fast if the
# directory cannot be created.
_STORAGE_DIR = Path(__file__).resolve().parents[3] / "backend" / "storage" / "uploads"


def _ensure_storage_dir() -> Path:
    """Create the storage directory if it does not exist and return its path."""
    _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return _STORAGE_DIR


# In-memory store: document_id -> DocumentMetadata
# Intentionally a module-level dict; data is lost on process restart.
_metadata_store: dict[str, DocumentMetadata] = {}


def store_pdf(original_filename: str, file_bytes: bytes) -> DocumentMetadata:
    """
    Persist an accepted PDF to local storage and record its metadata.

    Args:
        original_filename: The client-provided filename (used only as metadata,
                           never as the stored filename).
        file_bytes: Validated PDF bytes ready to write.

    Returns:
        DocumentMetadata for the stored file.

    Raises:
        OSError: If the file cannot be written to disk.
    """
    storage_dir = _ensure_storage_dir()

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
    )
    _metadata_store[document_id] = metadata
    return metadata


def get_metadata(document_id: str) -> DocumentMetadata | None:
    """Return stored metadata for a document_id, or None if not found."""
    return _metadata_store.get(document_id)


def list_metadata() -> list[DocumentMetadata]:
    """Return all in-memory metadata records."""
    return list(_metadata_store.values())

