"""Integration tests for document status, extraction, and orchestrator lifecycle."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.extraction import (
    DocumentExtractionResult,
    EntityLabel,
    EntityProvenance,
    ExtractionJobStatus,
    ExtractedEntity,
    ExtractedRelationship,
    RelationType,
)
from app.services.document_parser import DocumentParseError, ParsedChunk, ParsedDocument
from app.services.extraction_orchestrator import (
    ExtractionMetadataStore,
    ExtractionOrchestrator,
    default_orchestrator,
)
from app.services.knowledge_extractor import KnowledgeExtractionError

client = TestClient(app)


def _minimal_pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n190\n%%EOF"
    )


def _make_dummy_extraction(doc_id: str, original_filename: str) -> DocumentExtractionResult:
    return DocumentExtractionResult(
        schema_version="1.0",
        doc_id=doc_id,
        original_filename=original_filename,
        model_id="qwen2.5:7b",
        page_count=2,
        summary="Test extraction summary for document verification.",
        entities=[
            ExtractedEntity(
                canonical_id=f"paper::{doc_id}",
                label=EntityLabel.PAPER,
                name=original_filename,
                aliases=[],
                description=f"Uploaded document {original_filename}",
                provenance=[EntityProvenance(doc_id=doc_id, page_numbers=[1], section_heading="Root")],
            ),
            ExtractedEntity(
                canonical_id="method::transformer",
                label=EntityLabel.METHOD,
                name="Transformer",
                aliases=[],
                description="Attention architecture",
                provenance=[EntityProvenance(doc_id=doc_id, page_numbers=[1, 2], section_heading="Model")],
            ),
        ],
        relationships=[
            ExtractedRelationship(
                relationship_id=f"paper::{doc_id}--USES_METHOD--method::transformer",
                source_id=f"paper::{doc_id}",
                target_id="method::transformer",
                type=RelationType.USES_METHOD,
                evidence="We utilize the Transformer architecture.",
                doc_id=doc_id,
                page_number=1,
            )
        ],
        warnings=[],
    )


class TestDocumentStatusRouter:
    def test_nonexistent_document_returns_404(self):
        resp = client.get("/api/documents/nonexistent-doc-999/status")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_queued_document_status_retrieval(self, tmp_path):
        doc_id = "doc-status-test"
        default_orchestrator.metadata_store.upsert_status(
            doc_id=doc_id,
            original_filename="sample.pdf",
            status=ExtractionJobStatus.QUEUED,
        )

        resp = client.get(f"/api/documents/{doc_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["doc_id"] == doc_id
        assert data["status"] == "queued"
        assert data["original_filename"] == "sample.pdf"


class TestDocumentExtractionRouter:
    def test_nonexistent_document_returns_404(self):
        resp = client.get("/api/documents/nonexistent-doc-999/extraction")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_incomplete_extraction_returns_409(self):
        doc_id = "doc-in-progress"
        default_orchestrator.metadata_store.upsert_status(
            doc_id=doc_id,
            original_filename="test.pdf",
            status=ExtractionJobStatus.PARSING,
        )

        resp = client.get(f"/api/documents/{doc_id}/extraction")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "EXTRACTION_NOT_READY"

    def test_completed_extraction_returns_payload(self, tmp_path):
        doc_id = "doc-completed"
        filename = "attention.pdf"
        extraction = _make_dummy_extraction(doc_id, filename)

        # Write fake extraction result into orchestrator directory
        out_file = default_orchestrator.extracted_dir / f"{doc_id}.json"
        out_file.write_text(extraction.model_dump_json(indent=2), encoding="utf-8")

        default_orchestrator.metadata_store.upsert_status(
            doc_id=doc_id,
            original_filename=filename,
            status=ExtractionJobStatus.COMPLETED,
            page_count=2,
            entity_count=len(extraction.entities),
            relationship_count=len(extraction.relationships),
        )

        resp = client.get(f"/api/documents/{doc_id}/extraction")
        assert resp.status_code == 200
        data = resp.json()
        assert data["doc_id"] == doc_id
        assert data["schema_version"] == "1.0"
        assert len(data["entities"]) == 2
        assert len(data["relationships"]) == 1
        assert data["relationships"][0]["type"] == "USES_METHOD"


class TestDocumentReExtractionTrigger:
    def test_nonexistent_document_extract_returns_404(self):
        resp = client.post("/api/documents/nonexistent-doc-999/extract")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_in_progress_re_extract_returns_409(self):
        doc_id = "doc-busy"
        default_orchestrator.metadata_store.upsert_status(
            doc_id=doc_id,
            original_filename="busy.pdf",
            status=ExtractionJobStatus.EXTRACTING,
        )

        resp = client.post(f"/api/documents/{doc_id}/extract")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "EXTRACTION_IN_PROGRESS"

    @patch.object(ExtractionOrchestrator, "run_extraction")
    def test_failed_document_can_re_extract_202(self, mock_run):
        doc_id = "doc-retry"
        default_orchestrator.metadata_store.upsert_status(
            doc_id=doc_id,
            original_filename="retry.pdf",
            status=ExtractionJobStatus.FAILED,
            error_code="OLLAMA_TIMEOUT",
        )

        resp = client.post(f"/api/documents/{doc_id}/extract")
        assert resp.status_code == 202
        assert resp.json()["status"] == "queued"
        mock_run.assert_called_once_with(doc_id, "retry.pdf")


class TestOrchestratorErrorTransitions:
    def test_parser_failure_transitions_to_failed(self, tmp_path):
        doc_id = "doc-fail-parse"
        filename = "corrupt.pdf"

        # Create dummy pdf file in upload dir
        pdf_file = default_orchestrator.upload_dir / f"{doc_id}.pdf"
        pdf_file.write_bytes(b"%PDF-invalid")

        mock_parser = MagicMock()
        mock_parser.parse_pdf.side_effect = DocumentParseError(
            "Docling could not parse PDF", code="DOCLING_PARSE_ERROR"
        )

        orchestrator = ExtractionOrchestrator(
            parser=mock_parser,
            metadata_store=default_orchestrator.metadata_store,
            upload_dir=default_orchestrator.upload_dir,
            extracted_dir=default_orchestrator.extracted_dir,
        )

        orchestrator.run_extraction(doc_id, filename)
        status = orchestrator.metadata_store.get_status(doc_id)
        assert status is not None
        assert status.status == ExtractionJobStatus.FAILED
        assert status.error_code == "DOCLING_PARSE_ERROR"

    def test_ollama_timeout_transitions_to_failed(self, tmp_path):
        doc_id = "doc-fail-ollama"
        filename = "slow.pdf"

        pdf_file = default_orchestrator.upload_dir / f"{doc_id}.pdf"
        pdf_file.write_bytes(_minimal_pdf_bytes())

        mock_parser = MagicMock()
        mock_parser.parse_pdf.return_value = ParsedDocument(
            page_count=1,
            chunks=[ParsedChunk(chunk_index=0, section_heading="Intro", page_numbers=[1], content="text")],
        )

        mock_extractor = MagicMock()
        mock_extractor.extract_document.side_effect = KnowledgeExtractionError(
            "Local Ollama timed out.", code="OLLAMA_TIMEOUT"
        )

        orchestrator = ExtractionOrchestrator(
            parser=mock_parser,
            extractor=mock_extractor,
            metadata_store=default_orchestrator.metadata_store,
            upload_dir=default_orchestrator.upload_dir,
            extracted_dir=default_orchestrator.extracted_dir,
        )

        orchestrator.run_extraction(doc_id, filename)
        status = orchestrator.metadata_store.get_status(doc_id)
        assert status is not None
        assert status.status == ExtractionJobStatus.FAILED
        assert status.error_code == "OLLAMA_TIMEOUT"
