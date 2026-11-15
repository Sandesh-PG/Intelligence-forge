from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from app.schemas.extraction import (
    DocumentExtractionResult,
    DocumentStatusResponse,
    ExtractionJobStatus,
)
from app.services.extraction_orchestrator import default_orchestrator as orchestrator
from app.services.storage import get_metadata

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
def get_document_status(doc_id: str) -> DocumentStatusResponse:
    record = orchestrator.metadata_store.get_status(doc_id)
    if not record:
        mem_meta = get_metadata(doc_id)
        if mem_meta:
            return orchestrator.queue_document(doc_id=doc_id, original_filename=mem_meta.original_filename)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document record not found."},
        )
    return record


@router.get("/{doc_id}/extraction", response_model=DocumentExtractionResult)
def get_document_extraction(doc_id: str) -> DocumentExtractionResult:
    record = orchestrator.metadata_store.get_status(doc_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document record not found."},
        )

    if record.status != ExtractionJobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXTRACTION_NOT_READY",
                "message": f"Extraction is currently in '{record.status.value}' state.",
            },
        )

    extraction = orchestrator.load_extraction(doc_id)
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Extraction artifact missing."},
        )
    return extraction


@router.post("/{doc_id}/extract", response_model=DocumentStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_document_extraction(doc_id: str, background_tasks: BackgroundTasks) -> DocumentStatusResponse:
    record = orchestrator.metadata_store.get_status(doc_id)
    if not record:
        mem_meta = get_metadata(doc_id)
        if mem_meta:
            record = orchestrator.queue_document(doc_id=doc_id, original_filename=mem_meta.original_filename)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document record not found."},
            )

    if record.status in {ExtractionJobStatus.PARSING, ExtractionJobStatus.EXTRACTING}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EXTRACTION_IN_PROGRESS", "message": "Extraction is already running."},
        )

    queued = orchestrator.queue_document(doc_id=doc_id, original_filename=record.original_filename)
    background_tasks.add_task(orchestrator.run_extraction, doc_id, record.original_filename)
    return queued
