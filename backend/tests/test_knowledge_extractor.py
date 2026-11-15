"""Unit tests for LocalKnowledgeExtractor, canonical ID normalization, and integrity checks."""

from unittest.mock import MagicMock, patch
import httpx
import pytest
from pydantic import ValidationError

from app.schemas.extraction import (
    EntityLabel,
    RawChunkExtraction,
    RawLLMEdge,
    RawLLMNode,
    RelationType,
)
from app.services.document_parser import ParsedChunk, ParsedDocument
from app.services.knowledge_extractor import (
    KnowledgeExtractionError,
    LocalKnowledgeExtractor,
    build_canonical_id,
    normalize_entity_name,
)


class TestCanonicalIdNormalization:
    def test_name_cleaning(self):
        assert normalize_entity_name("  Graph Neural Networks.  ") == "graph neural networks"
        assert normalize_entity_name("Attention Is All You Need;;") == "attention is all you need"
        assert normalize_entity_name("BERT: Pre-training of Deep...\n") == "bert: pre-training of deep"

    def test_canonical_id_format(self):
        cid = build_canonical_id(EntityLabel.CONCEPT, "  Knowledge Graph  ")
        assert cid == "concept::knowledge graph"
        assert cid.startswith("concept::")

    def test_root_paper_synthesis(self):
        extractor = LocalKnowledgeExtractor()
        parsed_doc = ParsedDocument(page_count=3, chunks=[])
        result = extractor.normalize_and_validate(
            doc_id="doc-456",
            original_filename="attention_paper.pdf",
            page_count=3,
            chunk_results=[],
        )
        assert any(e.canonical_id == "paper::doc-456" for e in result.entities)
        root = next(e for e in result.entities if e.canonical_id == "paper::doc-456")
        assert root.label == EntityLabel.PAPER
        assert root.name == "attention_paper.pdf"
        assert root.provenance[0].page_numbers == [1]


class TestCrossChunkDeduplication:
    def test_merges_pages_and_aliases(self):
        extractor = LocalKnowledgeExtractor()
        chunk1 = ParsedChunk(chunk_index=0, section_heading="Intro", page_numbers=[1, 2], content="...")
        raw1 = RawChunkExtraction(
            chunk_summary="Summary of chunk 1",
            entities=[
                RawLLMNode(
                    label=EntityLabel.METHOD,
                    name="Transformer",
                    aliases=["Transformer Architecture"],
                    description="Self-attention model.",
                )
            ],
            relationships=[],
        )

        chunk2 = ParsedChunk(chunk_index=1, section_heading="Methods", page_numbers=[2, 3], content="...")
        raw2 = RawChunkExtraction(
            chunk_summary="Summary of chunk 2",
            entities=[
                RawLLMNode(
                    label=EntityLabel.METHOD,
                    name="transformer",
                    aliases=["Attention Model"],
                    description="A deep learning architecture based on multi-head attention.",
                )
            ],
            relationships=[],
        )

        result = extractor.normalize_and_validate(
            doc_id="doc-dedup",
            original_filename="paper.pdf",
            page_count=3,
            chunk_results=[(chunk1, raw1), (chunk2, raw2)],
        )

        trans_entity = next(e for e in result.entities if e.canonical_id == "method::transformer")
        # Merged page numbers
        assert trans_entity.provenance[0].page_numbers == [1, 2, 3]
        # Preserved longer description
        assert "multi-head attention" in (trans_entity.description or "")
        # Aliases merged and deduplicated
        assert "Transformer Architecture" in trans_entity.aliases
        assert "Attention Model" in trans_entity.aliases
        assert "transformer" not in [a.lower() for a in trans_entity.aliases]


class TestReferentialIntegrity:
    def test_strips_self_loops_with_warning(self):
        extractor = LocalKnowledgeExtractor()
        chunk = ParsedChunk(chunk_index=0, section_heading="Intro", page_numbers=[1], content="...")
        raw = RawChunkExtraction(
            chunk_summary="Summary of self loop",
            entities=[
                RawLLMNode(label=EntityLabel.CONCEPT, name="Self Attention"),
            ],
            relationships=[
                RawLLMEdge(
                    source_label=EntityLabel.CONCEPT,
                    source_name="Self Attention",
                    target_label=EntityLabel.CONCEPT,
                    target_name="Self Attention",
                    type=RelationType.RELATED_TO,
                    evidence="Self attention attends to self.",
                )
            ],
        )

        result = extractor.normalize_and_validate(
            doc_id="doc-loop",
            original_filename="paper.pdf",
            page_count=1,
            chunk_results=[(chunk, raw)],
        )
        assert len(result.relationships) == 0
        assert any("Dropped self-loop relationship" in w for w in result.warnings)

    def test_strips_orphan_edges_with_warning(self):
        extractor = LocalKnowledgeExtractor()
        chunk = ParsedChunk(chunk_index=0, section_heading="Intro", page_numbers=[1], content="...")
        raw = RawChunkExtraction(
            chunk_summary="Summary of orphan edge",
            entities=[
                RawLLMNode(label=EntityLabel.METHOD, name="BERT"),
            ],
            relationships=[
                RawLLMEdge(
                    source_label=EntityLabel.METHOD,
                    source_name="BERT",
                    target_label=EntityLabel.DATASET,
                    target_name="GLUE Benchmark",  # Not present in entities list
                    type=RelationType.EVALUATED_ON,
                    evidence="Evaluated on GLUE benchmark.",
                )
            ],
        )

        result = extractor.normalize_and_validate(
            doc_id="doc-orphan",
            original_filename="paper.pdf",
            page_count=1,
            chunk_results=[(chunk, raw)],
        )
        assert len(result.relationships) == 0
        assert any("Dropped orphan relationship" in w for w in result.warnings)


class TestEnumSchemaValidation:
    def test_unapproved_entity_label_rejected(self):
        with pytest.raises(ValidationError):
            RawLLMNode(
                label="Algorithm",  # Invalid enum value
                name="QuickSort",
            )

    def test_unapproved_relation_type_rejected(self):
        with pytest.raises(ValidationError):
            RawLLMEdge(
                source_label=EntityLabel.METHOD,
                source_name="BERT",
                target_label=EntityLabel.CONCEPT,
                target_name="NLP",
                type="INVENTED_BY",  # Invalid enum value
                evidence="Invented by Google.",
            )


class TestLocalOllamaErrorHandling:
    @patch("httpx.Client.post")
    def test_ollama_timeout_maps_to_error_code(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("Connection timed out.")
        extractor = LocalKnowledgeExtractor()
        chunk = ParsedChunk(chunk_index=0, section_heading="Intro", page_numbers=[1], content="content")

        with pytest.raises(KnowledgeExtractionError) as exc_info:
            extractor._call_ollama_structured(chunk)
        assert exc_info.value.code == "OLLAMA_TIMEOUT"

    @patch("httpx.Client.post")
    def test_ollama_unavailable_maps_to_error_code(self, mock_post):
        mock_post.side_effect = httpx.ConnectError("Cannot reach localhost:11434")
        extractor = LocalKnowledgeExtractor()
        chunk = ParsedChunk(chunk_index=0, section_heading="Intro", page_numbers=[1], content="content")

        with pytest.raises(KnowledgeExtractionError) as exc_info:
            extractor._call_ollama_structured(chunk)
        assert exc_info.value.code == "OLLAMA_UNAVAILABLE"

    @patch("httpx.Client.post")
    def test_invalid_json_schema_maps_to_error_code(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": "not a json object"}
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        extractor = LocalKnowledgeExtractor()
        chunk = ParsedChunk(chunk_index=0, section_heading="Intro", page_numbers=[1], content="content")

        with pytest.raises(KnowledgeExtractionError) as exc_info:
            extractor._call_ollama_structured(chunk)
        assert exc_info.value.code == "EXTRACTION_SCHEMA_INVALID"

    @patch.object(LocalKnowledgeExtractor, "_call_ollama_structured")
    def test_retry_on_schema_invalid(self, mock_call):
        # Fails once with schema invalid, then succeeds on retry
        chunk = ParsedChunk(chunk_index=0, section_heading="Intro", page_numbers=[1], content="content")
        expected = RawChunkExtraction(
            chunk_summary="Valid summary on attempt 2",
            entities=[],
            relationships=[],
        )
        mock_call.side_effect = [
            KnowledgeExtractionError("Invalid schema", code="EXTRACTION_SCHEMA_INVALID"),
            expected,
        ]

        extractor = LocalKnowledgeExtractor()
        res = extractor._extract_chunk_with_retry(chunk)
        assert res.chunk_summary == "Valid summary on attempt 2"
        assert mock_call.call_count == 2
