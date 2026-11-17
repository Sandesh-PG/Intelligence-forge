import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.embedding_service import EmbeddingService, _fallback_hash_embedding
from app.services.global_web_agent import GlobalWebAgent, WebCitation
from app.services.privacy_guard import PrivacyGuard

client = TestClient(app)


class TestEmbeddingService:
    def test_fallback_hash_embedding_deterministic(self):
        vec1 = _fallback_hash_embedding("Deep residual learning for image recognition", dim=128)
        vec2 = _fallback_hash_embedding("Deep residual learning for image recognition", dim=128)
        assert len(vec1) == 128
        assert vec1 == vec2
        assert any(x != 0.0 for x in vec1)

    def test_cosine_similarity(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        assert pytest.approx(EmbeddingService.cosine_similarity(v1, v2)) == 1.0

        v3 = [0.0, 1.0, 0.0]
        assert pytest.approx(EmbeddingService.cosine_similarity(v1, v3)) == 0.0

        assert EmbeddingService.cosine_similarity([], v1) == 0.0
        assert EmbeddingService.cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    def test_embed_text_fallback_on_unreachable_ollama(self):
        vec = EmbeddingService.embed_text_sync("Test research query")
        assert len(vec) == 128
        assert any(x != 0.0 for x in vec)


class TestZeroLeakagePrivacyGuard:
    def test_strips_filenames_paths_and_uuids(self):
        question = "What does confidential_report.pdf say about project at C:\\users\\secret\\doc.txt or /var/data/leak.csv with uuid 12345678-1234-5678-1234-567812345678?"
        local_filenames = ["confidential_report.pdf"]
        local_chunks = ["Some text from the document."]

        res = PrivacyGuard.sanitize_for_public_web(
            user_question=question,
            missing_concepts=[],
            local_chunks=local_chunks,
            local_filenames=local_filenames,
        )

        assert "confidential_report" not in res.sanitized_query
        assert "C:\\" not in res.sanitized_query
        assert "doc.txt" not in res.sanitized_query
        assert "leak.csv" not in res.sanitized_query
        assert "12345678-1234-5678-1234-567812345678" not in res.sanitized_query
        assert len(res.redacted_terms) > 0

    def test_blocks_verbatim_4word_passages_from_local_papers(self):
        verbatim_passage = "the proprietary quantum entanglement throughput increased fivefold"
        local_chunks = [
            f"In our experiments, {verbatim_passage} compared to previous baselines."
        ]

        leaky_query = f"Can you explain why {verbatim_passage} in external literature?"
        res = PrivacyGuard.sanitize_for_public_web(
            user_question=leaky_query,
            missing_concepts=[],
            local_chunks=local_chunks,
            local_filenames=["quantum.pdf"],
        )

        assert verbatim_passage not in res.sanitized_query
        assert "proprietary quantum entanglement throughput" not in res.sanitized_query

    def test_blocks_unsafe_query_when_nothing_remains(self):
        local_chunks = ["unique proprietary secret algorithm"]
        res = PrivacyGuard.sanitize_for_public_web(
            user_question="unique proprietary secret algorithm",
            missing_concepts=[],
            local_chunks=local_chunks,
            local_filenames=[],
        )
        assert res.is_safe is False
        assert res.blocked_reason is not None


class TestMultiPageVectorRetrieval:
    def test_retrieval_across_multi_page_document(self, tmp_path):
        doc_id = "test-multipage-doc"
        paper_artifact = {
            "source_filename": "multimodal_survey.pdf",
            "doc_id": doc_id,
            "page_count": 5,
            "summary": "A comprehensive survey of multimodal artificial intelligence agents.",
            "pages": [
                {"page_number": 1, "text": "Introduction to artificial intelligence systems and foundational architectures."},
                {"page_number": 2, "text": "Related work covering computer vision models and recurrent networks."},
                {"page_number": 3, "text": "Evaluation metrics including BLEU, ROUGE, and CIDEr across benchmarks."},
                {"page_number": 4, "text": "Sophia and Erica are interactive humanoid robotics agents deployed by Hanson Robotics and BT Group."},
                {"page_number": 5, "text": "Future ethical considerations and safety frameworks for embodied intelligence."},
            ],
            "entities": [
                {
                    "canonical_id": "concept::humanoid_robotics",
                    "label": "Concept",
                    "name": "Humanoid Robotics",
                    "description": "Interactive embodied robotics platforms",
                    "provenance": [{"doc_id": doc_id, "page_numbers": [4]}],
                }
            ],
            "relationships": [],
        }

        artifact_file = settings.extracted_storage_dir / f"{doc_id}.json"
        artifact_file.write_text(json.dumps(paper_artifact), encoding="utf-8")

        from app.routers.chat import create_chat, send_message
        from app.schemas.chat import CreateChatRequest, SendMessageRequest

        session_obj = create_chat(CreateChatRequest(title="Multi-page Test", doc_ids=[doc_id]))
        session_id = session_obj.id

        with patch("app.services.graphrag_qa_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": {
                    "content": "Sophia and Erica were deployed by Hanson Robotics and BT Group [multimodal_survey.pdf, p. 4].\nCOVERAGE: COMPLETE",
                }
            }
            mock_client.post.return_value = mock_resp

        import asyncio

        data = asyncio.run(
            send_message(
                session_id=session_id,
                payload=SendMessageRequest(content="Where were Sophia and Erica deployed?", allow_web_search=True),
            )
        )
        citations = data.assistant_message.citations
        assert len(citations) > 0
        assert any(c.page_number == 4 and "Sophia" in c.snippet for c in citations)


class TestDualAgentRouting:
    def test_local_agent_complete_coverage_does_not_call_web_search(self):
        doc_id = "doc-complete-coverage"
        paper_artifact = {
            "source_filename": "resnet.pdf",
            "doc_id": doc_id,
            "page_count": 2,
            "summary": "Deep Residual Learning for Image Recognition introduces skip connections.",
            "pages": [
                {"page_number": 1, "text": "Residual connections allow training of 152 layer networks."},
                {"page_number": 2, "text": "On ImageNet, ResNet achieves 3.57% top-5 error, winning ILSVRC 2015."},
            ],
            "entities": [],
            "relationships": [],
        }
        artifact_file = settings.extracted_storage_dir / f"{doc_id}.json"
        artifact_file.write_text(json.dumps(paper_artifact), encoding="utf-8")

        from app.routers.chat import create_chat, send_message
        from app.schemas.chat import CreateChatRequest, SendMessageRequest
        import asyncio

        session_obj = create_chat(CreateChatRequest(title="Complete Coverage Test", doc_ids=[doc_id]))
        session_id = session_obj.id

        with patch("app.services.graphrag_qa_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": {
                    "content": "ResNet achieves 3.57% top-5 error on ImageNet [resnet.pdf, p. 2].\nCOVERAGE: COMPLETE",
                }
            }
            mock_client.post.return_value = mock_resp

            with patch.object(GlobalWebAgent, "search_and_synthesize") as mock_web_search:
                data = asyncio.run(
                    send_message(
                        session_id=session_id,
                        payload=SendMessageRequest(
                            content="What was the top-5 error of ResNet on ImageNet?",
                            allow_web_search=True,
                        ),
                    )
                )

                assert mock_web_search.call_count == 0
                trace = data.assistant_message.agent_trace
                assert trace is not None
                assert trace["local_agent_used"] is True
                assert trace["web_agent_used"] is False
                assert len(data.assistant_message.web_citations) == 0
                assert "3.57%" in data.assistant_message.content
                assert "COVERAGE: COMPLETE" not in data.assistant_message.content

    def test_insufficient_coverage_invokes_sanitized_web_fallback(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_global_web_agent", True)
        doc_id = "doc-partial-coverage"
        paper_artifact = {
            "source_filename": "internal_paper.pdf",
            "doc_id": doc_id,
            "page_count": 1,
            "summary": "A discussion on neural network optimizers.",
            "pages": [
                {"page_number": 1, "text": "We evaluate SGD and AdamW on CIFAR-10."},
            ],
            "entities": [],
            "relationships": [],
        }
        artifact_file = settings.extracted_storage_dir / f"{doc_id}.json"
        artifact_file.write_text(json.dumps(paper_artifact), encoding="utf-8")

        from app.routers.chat import create_chat, send_message
        from app.schemas.chat import CreateChatRequest, SendMessageRequest
        import asyncio

        session_obj = create_chat(CreateChatRequest(title="Partial Coverage Test", doc_ids=[doc_id]))
        session_id = session_obj.id

        with patch("app.services.graphrag_qa_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": {
                    "content": "The paper internal_paper.pdf only evaluates SGD and AdamW.\nCOVERAGE: INSUFFICIENT | MISSING: Muon optimizer",
                }
            }
            mock_client.post.return_value = mock_resp

            with patch.object(
                GlobalWebAgent,
                "search_and_synthesize",
                new_callable=AsyncMock,
                return_value=(
                    "Muon is an efficient matrix optimizer designed by Keller Jordan.",
                    [WebCitation(title="Muon Optimizer", url="https://example.com/muon", snippet="Muon details")],
                ),
            ) as mock_web_search:
                data = asyncio.run(
                    send_message(
                        session_id=session_id,
                        payload=SendMessageRequest(
                            content="What is the Muon optimizer mentioned in internal_paper.pdf?",
                            allow_web_search=True,
                        ),
                    )
                )

                # Web search MUST be invoked
                assert mock_web_search.call_count == 1
                called_query, _ = mock_web_search.call_args[0]
                # The filename 'internal_paper.pdf' must NOT leak into the public web search query!
                assert "internal_paper.pdf" not in called_query
                assert "internal_paper" not in called_query

                trace = data.assistant_message.agent_trace
                assert trace is not None
                assert trace["local_agent_used"] is True
                assert trace["web_agent_used"] is True
                assert trace["privacy_verified"] is True
                assert len(data.assistant_message.web_citations) == 1
                assert "From Uploaded Research Papers" in data.assistant_message.content
                assert "External Web Context" in data.assistant_message.content
