import json
from datetime import datetime, timezone
from pathlib import Path
from app.core.config import settings
from app.schemas.extraction import (
    DocumentExtractionResult,
    DocumentStatusResponse,
    ExtractionJobStatus,
)
from app.services.document_parser import DocumentParseError, LocalDocumentParser
from app.services.knowledge_extractor import KnowledgeExtractionError, LocalKnowledgeExtractor


class ExtractionMetadataStore:
    """Thread-safe/atomic JSON metadata store for document extraction states."""

    def __init__(self, metadata_path: Path | None = None) -> None:
        self.metadata_path = metadata_path or settings.metadata_storage_path
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> dict[str, dict]:
        if not self.metadata_path.exists():
            return {}
        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_all(self, data: dict[str, dict]) -> None:
        tmp_path = self.metadata_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(self.metadata_path)

    def upsert_status(
        self,
        doc_id: str,
        original_filename: str,
        status: ExtractionJobStatus,
        page_count: int | None = None,
        entity_count: int | None = None,
        relationship_count: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        session_id: str | None = None,
    ) -> DocumentStatusResponse:
        all_records = self._read_all()
        existing = all_records.get(doc_id, {})
        now = datetime.now(timezone.utc)
        record = {
            "doc_id": doc_id,
            "original_filename": original_filename or existing.get("original_filename", ""),
            "status": status.value,
            "page_count": page_count if page_count is not None else existing.get("page_count"),
            "entity_count": entity_count if entity_count is not None else existing.get("entity_count"),
            "relationship_count": relationship_count if relationship_count is not None else existing.get("relationship_count"),
            "error_code": error_code,
            "error_message": error_message,
            "updated_at": now.isoformat(),
            "session_id": session_id or existing.get("session_id"),
        }
        all_records[doc_id] = record
        self._write_all(all_records)
        return DocumentStatusResponse.model_validate(record)

    def get_status(self, doc_id: str) -> DocumentStatusResponse | None:
        all_records = self._read_all()
        record = all_records.get(doc_id)
        if not record:
            return None
        return DocumentStatusResponse.model_validate(record)

    def delete_status(self, doc_id: str) -> bool:
        all_records = self._read_all()
        if doc_id in all_records:
            del all_records[doc_id]
            self._write_all(all_records)
            return True
        return False


class ExtractionOrchestrator:
    def __init__(
        self,
        parser: LocalDocumentParser | None = None,
        extractor: LocalKnowledgeExtractor | None = None,
        metadata_store: ExtractionMetadataStore | None = None,
        upload_dir: Path | None = None,
        extracted_dir: Path | None = None,
    ) -> None:
        self.parser = parser or LocalDocumentParser()
        self.extractor = extractor or LocalKnowledgeExtractor()
        self.metadata_store = metadata_store or ExtractionMetadataStore()
        self.upload_dir = upload_dir or settings.upload_storage_dir
        self.extracted_dir = extracted_dir or settings.extracted_storage_dir
        self.extracted_dir.mkdir(parents=True, exist_ok=True)

    def queue_document(self, doc_id: str, original_filename: str, session_id: str | None = None) -> DocumentStatusResponse:
        return self.metadata_store.upsert_status(
            doc_id=doc_id,
            original_filename=original_filename,
            status=ExtractionJobStatus.QUEUED,
            session_id=session_id,
        )

    def run_extraction(self, doc_id: str, original_filename: str) -> None:
        """Run the full extraction pipeline for a document and optionally persist to Neo4j.

        If ``settings.neo4j_auto_sync`` is true, the extracted result is upserted into Neo4j via ``GraphService``.
        Errors in graph persistence are recorded with a ``GRAPH_PERSIST_ERROR`` status code but do not affect the
        successful completion of the extraction itself.
        """
        pdf_path = self.upload_dir / f"{doc_id}.pdf"
        output_path = self.extracted_dir / f"{doc_id}.json"

        try:
            self.metadata_store.upsert_status(
                doc_id=doc_id,
                original_filename=original_filename,
                status=ExtractionJobStatus.PARSING,
            )
            parsed_doc = self.parser.parse_pdf(pdf_path)

            self.metadata_store.upsert_status(
                doc_id=doc_id,
                original_filename=original_filename,
                status=ExtractionJobStatus.EXTRACTING,
                page_count=parsed_doc.page_count,
            )
            extraction_result = self.extractor.extract_document(
                doc_id=doc_id,
                original_filename=original_filename,
                parsed_doc=parsed_doc,
            )

            tmp_out = output_path.with_suffix(".tmp")
            tmp_out.write_text(extraction_result.model_dump_json(indent=2), encoding="utf-8")
            tmp_out.replace(output_path)

            self.metadata_store.upsert_status(
                doc_id=doc_id,
                original_filename=original_filename,
                status=ExtractionJobStatus.COMPLETED,
                page_count=extraction_result.page_count,
                entity_count=len(extraction_result.entities),
                relationship_count=len(extraction_result.relationships),
            )
            # Auto-sync to Neo4j if enabled
            if getattr(settings, "neo4j_auto_sync", False) and settings.neo4j_uri:
                try:
                    from app.services.graph_persistence_service import GraphPersistenceService
                    sync_res = GraphPersistenceService.persist_document_graph(doc_id)
                    if sync_res.status == "failed":
                        self.metadata_store.upsert_status(
                            doc_id=doc_id,
                            original_filename=original_filename,
                            status=ExtractionJobStatus.COMPLETED,
                            error_code=sync_res.error_code or "GRAPH_PERSIST_ERROR",
                            error_message=sync_res.error_message or "Graph persistence failed",
                        )
                except Exception as exc:
                    # Record graph persistence error without overriding successful extraction status
                    self.metadata_store.upsert_status(
                        doc_id=doc_id,
                        original_filename=original_filename,
                        status=ExtractionJobStatus.COMPLETED,
                        error_code="GRAPH_PERSIST_ERROR",
                        error_message=str(exc),
                    )
        except (DocumentParseError, KnowledgeExtractionError) as exc:
            self.metadata_store.upsert_status(
                doc_id=doc_id,
                original_filename=original_filename,
                status=ExtractionJobStatus.FAILED,
                error_code=exc.code,
                error_message=exc.message,
            )
        except Exception:
            self.metadata_store.upsert_status(
                doc_id=doc_id,
                original_filename=original_filename,
                status=ExtractionJobStatus.FAILED,
                error_code="EXTRACTION_INTERNAL_ERROR",
                error_message="An unexpected internal error occurred during extraction.",
            )

    def load_extraction(self, doc_id: str) -> DocumentExtractionResult | None:
        output_path = self.extracted_dir / f"{doc_id}.json"
        if not output_path.exists():
            return None
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
            if not data.get("source_filename") and data.get("original_filename"):
                data["source_filename"] = data["original_filename"]
            if not data.get("original_filename") and data.get("source_filename"):
                data["original_filename"] = data["source_filename"]
            return DocumentExtractionResult.model_validate(data)
        except Exception:
            return None


default_orchestrator = ExtractionOrchestrator()