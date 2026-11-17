import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from app.core.config import settings
from app.schemas.extraction import (
    DocumentExtractionResult,
    DocumentStatusResponse,
    ExtractionJobStatus,
)
from app.schemas.graph import DocumentItemResponse
from app.services.chat_store import chat_store
from app.services.extraction_orchestrator import default_orchestrator as orchestrator
from app.services.graph_persistence_service import GraphPersistenceService
from app.services.neo4j_client import neo4j_driver
from app.services.storage import delete_metadata, get_metadata, list_metadata

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentItemResponse])
def list_documents(session_id: Optional[str] = Query(default=None)) -> list[DocumentItemResponse]:
    """
    List uploaded and extracted documents with summary, counts, and status.
    If session_id is provided, only documents attached to that chat session are returned.
    Sorted newest first.
    """
    if session_id:
        session = chat_store.get_session(session_id)
        if not session:
            return []
        allowed_ids = set(session.doc_ids)
    else:
        allowed_ids = None
    items_by_id: dict[str, dict] = {}

    # 1. In-memory uploads
    for mem in list_metadata():
        items_by_id[mem.document_id] = {
            "doc_id": mem.document_id,
            "filename": mem.original_filename,
            "file_size": mem.file_size_bytes,
            "page_count": 0,
            "extraction_status": "uploaded",
            "entity_count": 0,
            "relationship_count": 0,
            "summary": "",
            "created_at": mem.upload_timestamp.isoformat(),
            "synced_to_neo4j": False,
            "session_id": getattr(mem, "session_id", None),
        }

    # 2. Metadata store
    meta_records = orchestrator.metadata_store._read_all()
    for doc_id, meta in meta_records.items():
        existing = items_by_id.get(doc_id, {})
        items_by_id[doc_id] = {
            "doc_id": doc_id,
            "filename": meta.get("original_filename") or existing.get("filename", f"{doc_id}.pdf"),
            "file_size": existing.get("file_size", 0),
            "page_count": meta.get("page_count") or existing.get("page_count", 0),
            "extraction_status": meta.get("status", "uploaded"),
            "entity_count": meta.get("entity_count") or 0,
            "relationship_count": meta.get("relationship_count") or 0,
            "summary": existing.get("summary", ""),
            "created_at": meta.get("updated_at") or existing.get("created_at", ""),
            "synced_to_neo4j": False,
            "session_id": meta.get("session_id") or existing.get("session_id"),
        }

    # 3. Upload storage directory
    if settings.upload_storage_dir.exists():
        for pdf_path in settings.upload_storage_dir.glob("*.pdf"):
            doc_id = pdf_path.stem
            st = pdf_path.stat()
            if doc_id not in items_by_id:
                items_by_id[doc_id] = {
                    "doc_id": doc_id,
                    "filename": f"{doc_id}.pdf",
                    "file_size": st.st_size,
                    "page_count": 0,
                    "extraction_status": "uploaded",
                    "entity_count": 0,
                    "relationship_count": 0,
                    "summary": "",
                    "created_at": datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat(),
                    "synced_to_neo4j": False,
                }
            else:
                if items_by_id[doc_id]["file_size"] == 0:
                    items_by_id[doc_id]["file_size"] = st.st_size
                if not items_by_id[doc_id]["created_at"]:
                    items_by_id[doc_id]["created_at"] = datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat()

    # 4. Extracted storage directory
    if settings.extracted_storage_dir.exists():
        for json_path in settings.extracted_storage_dir.glob("*.json"):
            doc_id = json_path.stem
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                st = json_path.stat()
                existing = items_by_id.get(doc_id, {})
                filename = data.get("source_filename") or data.get("original_filename") or existing.get("filename", f"{doc_id}.pdf")
                entities = data.get("entities", [])
                relationships = data.get("relationships", [])
                summary = data.get("summary", "")
                page_count = data.get("page_count", 0)

                items_by_id[doc_id] = {
                    "doc_id": doc_id,
                    "filename": filename,
                    "file_size": existing.get("file_size", 0),
                    "page_count": page_count or existing.get("page_count", 0),
                    "extraction_status": "completed",
                    "entity_count": len(entities) if entities else existing.get("entity_count", 0),
                    "relationship_count": len(relationships) if relationships else existing.get("relationship_count", 0),
                    "summary": summary,
                    "created_at": existing.get("created_at") or datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat(),
                    "synced_to_neo4j": False,
                    "session_id": existing.get("session_id"),
                }
            except Exception:
                pass

    # 5. Check Neo4j sync state if configured
    if settings.neo4j_uri:
        try:
            driver = neo4j_driver.get_driver()
            with driver.session(database=settings.neo4j_database) as session:
                res = session.run("MATCH (n:Entity) RETURN DISTINCT n.source_doc_ids AS doc_ids")
                synced_docs = set()
                for rec in res:
                    for d in (rec["doc_ids"] or []):
                        synced_docs.add(d)
                for doc_id, item in items_by_id.items():
                    if doc_id in synced_docs:
                        item["synced_to_neo4j"] = True
        except Exception:
            pass

    results = [DocumentItemResponse(**data) for data in items_by_id.values()]
    if allowed_ids is not None:
        results = [doc for doc in results if doc.doc_id in allowed_ids]
    results.sort(key=lambda x: x.created_at, reverse=True)
    return results


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
def get_document_status(doc_id: str) -> DocumentStatusResponse:
    json_path = settings.extracted_storage_dir / f"{doc_id}.json"
    record = orchestrator.metadata_store.get_status(doc_id)
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            return DocumentStatusResponse(
                doc_id=doc_id,
                original_filename=data.get("source_filename") or data.get("original_filename") or (record.original_filename if record else f"{doc_id}.pdf"),
                status=ExtractionJobStatus.COMPLETED,
                page_count=data.get("page_count") or (record.page_count if record else 0),
                entity_count=len(data.get("entities", [])),
                relationship_count=len(data.get("relationships", [])),
                updated_at=record.updated_at if record else datetime.fromtimestamp(json_path.stat().st_mtime, tz=timezone.utc),
                session_id=record.session_id if record else None,
            )
        except Exception:
            pass

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
    # First check if extracted artifact exists and load it
    extraction = orchestrator.load_extraction(doc_id)
    if extraction:
        return extraction

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

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "DOCUMENT_NOT_FOUND", "message": "Extraction artifact missing."},
    )


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


@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
def delete_document(doc_id: str) -> dict:
    """
    Delete an uploaded paper, its extracted knowledge artifacts, metadata, and associated Neo4j graph nodes.
    """
    pdf_path = settings.upload_storage_dir / f"{doc_id}.pdf"
    json_path = settings.extracted_storage_dir / f"{doc_id}.json"
    status_record = orchestrator.metadata_store.get_status(doc_id)
    mem_record = get_metadata(doc_id)

    if not pdf_path.exists() and not json_path.exists() and not status_record and not mem_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": f"Document {doc_id} not found."},
        )

    # 1. Delete files on disk
    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except OSError:
            pass

    if json_path.exists():
        try:
            json_path.unlink()
        except OSError:
            pass

    # 2. Clean metadata
    delete_metadata(doc_id)
    orchestrator.metadata_store.delete_status(doc_id)

    # 3. Clean Neo4j graph if configured
    GraphPersistenceService.delete_document_graph(doc_id)

    return {"doc_id": doc_id, "deleted": True, "message": "Document successfully deleted."}
