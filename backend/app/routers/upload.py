"""
Upload router — POST /api/upload

Accepts a batch of PDF files (up to 3, each ≤ 20 MB, total ≤ 60 MB),
validates every file independently, stores accepted files, queues background
knowledge extraction, and returns an individual result for every file in the batch.

Rules enforced on the backend (not only in the UI):
- Maximum 3 files per batch.
- Maximum 20 MB per file.
- Maximum 60 MB combined batch size.
- Per-file validation: extension, MIME type, PDF header, readability,
  password-protection check.
- One invalid file does not reject the entire batch.
- Automatically triggers asynchronous document parsing and extraction on accepted files.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.core.config import settings
from app.schemas.upload import BatchUploadResponse, FileUploadResult, UploadStatus
from app.services.extraction_orchestrator import default_orchestrator as orchestrator
from app.services.file_validator import MAX_FILE_SIZE_BYTES, validate_pdf
from app.services.storage import store_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["upload"])

MAX_FILES_PER_BATCH = 3
MAX_BATCH_SIZE_BYTES = 60 * 1024 * 1024  # 60 MB


@router.post("/upload", response_model=BatchUploadResponse, status_code=200)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(default=[], description="PDF files to upload (max 3)"),
) -> BatchUploadResponse:
    """
    Upload and validate a batch of research-paper PDFs.

    - Validates each file independently.
    - Stores accepted files in the private backend storage directory.
    - Triggers asynchronous background extraction for accepted files.
    - Returns an individual result for every file in the batch.
    """
    # --- Batch-level checks (reject the entire request, not individual files) ---

    if len(files) == 0:
        raise HTTPException(status_code=422, detail="No files provided.")

    if len(files) > MAX_FILES_PER_BATCH:
        raise HTTPException(
            status_code=422,
            detail=(
                f"A batch may contain at most {MAX_FILES_PER_BATCH} files; "
                f"{len(files)} were submitted."
            ),
        )

    # Read all file bytes up front so we can enforce the combined-size limit
    # before doing any per-file work.
    file_contents: list[tuple[str, bytes]] = []
    total_bytes = 0

    for upload in files:
        raw = await upload.read()
        total_bytes += len(raw)
        file_contents.append((upload.filename or "", raw))

    if total_bytes > MAX_BATCH_SIZE_BYTES:
        total_mb = total_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=422,
            detail=(
                f"Combined batch size {total_mb:.1f} MB exceeds the 60 MB limit."
            ),
        )

    # --- Per-file validation and storage ---

    results: list[FileUploadResult] = []

    for filename, file_bytes in file_contents:
        # Individual size check (also enforced here, not only at batch level)
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            size_mb = len(file_bytes) / (1024 * 1024)
            results.append(
                FileUploadResult(
                    original_filename=filename,
                    status=UploadStatus.rejected,
                    rejection_reason=(
                        f"File size {size_mb:.1f} MB exceeds the 20 MB per-file limit."
                    ),
                )
            )
            continue

        validation = validate_pdf(filename, file_bytes)

        if not validation.is_valid:
            results.append(
                FileUploadResult(
                    original_filename=filename,
                    status=UploadStatus.rejected,
                    rejection_reason=validation.rejection_reason,
                )
            )
            continue

        # Persist the accepted file
        try:
            metadata = store_pdf(filename, file_bytes, destination_dir=settings.upload_storage_dir)
        except OSError:
            logger.exception("Failed to store uploaded file '%s'", filename)
            results.append(
                FileUploadResult(
                    original_filename=filename,
                    status=UploadStatus.rejected,
                    rejection_reason="Server error: the file could not be saved. Please try again.",
                )
            )
            continue

        # Trigger background extraction pipeline
        orchestrator.queue_document(doc_id=metadata.document_id, original_filename=filename)
        background_tasks.add_task(orchestrator.run_extraction, metadata.document_id, filename)

        results.append(
            FileUploadResult(
                original_filename=filename,
                document_id=metadata.document_id,
                status=UploadStatus.accepted,
            )
        )

    return BatchUploadResponse(results=results)
