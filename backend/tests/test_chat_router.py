import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.schemas.chat import CitationItem, WebCitation
from app.services.chat_store import chat_store
from app.services.graphrag_qa_service import GraphRAGQAService

client = TestClient(app)


class TestChatStoreDirect:
    def test_create_and_get_session(self):
        session = chat_store.create_session("My Research Project", ["doc-1", "doc-2"])
        assert session.id is not None
        assert session.title == "My Research Project"
        assert session.doc_ids == ["doc-1", "doc-2"]

        retrieved = chat_store.get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id
        assert retrieved.title == "My Research Project"
        assert retrieved.doc_ids == ["doc-1", "doc-2"]
        assert len(retrieved.messages) == 0

    def test_append_message_and_auto_title(self):
        session = chat_store.create_session("New Research Chat", [])
        msg = chat_store.append_message(
            session_id=session.id,
            role="user",
            content="What are the key contributions of Attention is All You Need?",
            citations=[],
            auto_title_from_first_user_msg=True,
        )
        assert msg.role == "user"
        assert "key contributions" in msg.content

        updated_session = chat_store.get_session(session.id)
        assert updated_session is not None
        assert updated_session.title.startswith("What are the key contributions")
        assert len(updated_session.messages) == 1

        # Append assistant message with citations
        cite = CitationItem(
            doc_id="doc-123",
            filename="attention.pdf",
            page_number=3,
            snippet="Multi-head attention mechanism...",
        )
        asst_msg = chat_store.append_message(
            session_id=session.id,
            role="assistant",
            content="The paper introduces the Transformer architecture.",
            citations=[cite],
        )
        assert asst_msg.role == "assistant"
        assert len(asst_msg.citations) == 1

        refreshed = chat_store.get_session(session.id)
        assert refreshed is not None
        assert len(refreshed.messages) == 2


class TestChatRouterAPI:
    def test_create_and_list_chats(self):
        resp = client.post("/api/chats", json={"title": "Session Alpha", "doc_ids": ["doc-101"]})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Session Alpha"
        assert data["doc_ids"] == ["doc-101"]
        session_id = data["id"]

        list_resp = client.get("/api/chats")
        assert list_resp.status_code == 200
        summaries = list_resp.json()
        assert any(s["id"] == session_id for s in summaries)

    def test_get_chat_details_success(self):
        created = client.post("/api/chats", json={"title": "Detail Session"}).json()
        session_id = created["id"]

        resp = client.get(f"/api/chats/{session_id}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["id"] == session_id
        assert detail["title"] == "Detail Session"
        assert detail["messages"] == []

    def test_get_nonexistent_chat_returns_404(self):
        resp = client.get("/api/chats/nonexistent-session-id-999")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "CHAT_SESSION_NOT_FOUND"

    def test_update_chat_documents(self):
        created = client.post("/api/chats", json={"title": "Doc Update Test"}).json()
        session_id = created["id"]

        patch_resp = client.patch(
            f"/api/chats/{session_id}/documents",
            json={"doc_ids": ["paper-alpha", "paper-beta"]},
        )
        assert patch_resp.status_code == 200
        summary = patch_resp.json()
        assert summary["doc_ids"] == ["paper-alpha", "paper-beta"]

        get_resp = client.get(f"/api/chats/{session_id}")
        assert get_resp.json()["doc_ids"] == ["paper-alpha", "paper-beta"]

    def test_delete_chat_session(self):
        created = client.post("/api/chats", json={"title": "To Delete"}).json()
        session_id = created["id"]

        del_resp = client.delete(f"/api/chats/{session_id}")
        assert del_resp.status_code == 200
        assert del_resp.json() == {"deleted": True}

        get_resp = client.get(f"/api/chats/{session_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_chat_returns_404(self):
        del_resp = client.delete("/api/chats/nonexistent-delete-999")
        assert del_resp.status_code == 404

    def test_export_chat_session_markdown(self):
        # 1. 404 for missing session
        missing_resp = client.get("/api/chats/nonexistent-session-export-999/export")
        assert missing_resp.status_code == 404
        assert missing_resp.json()["detail"]["code"] == "CHAT_SESSION_NOT_FOUND"

        # 2. Create session and messages
        created = client.post("/api/chats", json={"title": "Quantum Computing Analysis", "doc_ids": ["doc-qc-1"]}).json()
        session_id = created["id"]

        chat_store.append_message(
            session_id=session_id,
            role="user",
            content="What is the significance of Shor's algorithm?",
            citations=[],
        )
        chat_store.append_message(
            session_id=session_id,
            role="assistant",
            content="Shor's algorithm demonstrates polynomial time integer factorization.",
            citations=[
                CitationItem(
                    doc_id="doc-qc-1",
                    filename="quantum_algorithms.pdf",
                    page_number=5,
                    snippet="Shor's algorithm solves discrete logarithms in polynomial time.",
                )
            ],
            web_citations=[
                WebCitation(
                    title="Quantum Complexity Zoo",
                    url="https://example.com/quantum-zoo",
                    snippet="BQP complexity class overview.",
                )
            ],
            agent_trace={
                "local_agent_used": True,
                "web_agent_used": True,
                "privacy_verified": True,
            },
        )

        # 3. Export session markdown
        resp = client.get(f"/api/chats/{session_id}/export")
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers.get("content-type", "")
        assert f'attachment; filename="research-session-{session_id[:8]}.md"' in resp.headers.get("content-disposition", "")

        content = resp.text
        assert "# Quantum Computing Analysis" in content
        assert "## User" in content
        assert "What is the significance of Shor's algorithm?" in content
        assert "## Intelligence Forge Assistant" in content
        assert "Shor's algorithm demonstrates polynomial time integer factorization." in content
        assert "Local Grounded: Yes" in content
        assert "Web Fallback: Yes" in content
        assert "Privacy Verified: Yes" in content
        assert "Local Paper Citations" in content
        assert "quantum_algorithms.pdf, p. 5" in content
        assert "External Web Sources" in content
        assert "[Quantum Complexity Zoo](https://example.com/quantum-zoo)" in content

    def test_send_message_with_extracted_paper_fallback(self, tmp_path):
        # Create dummy extracted paper in isolated storage
        dummy_extraction = {
            "source_filename": "deep_residual_learning.pdf",
            "doc_id": "resnet-doc",
            "summary": "Deep Residual Learning for Image Recognition proposes residual connections.",
            "entities": [
                {
                    "canonical_id": "method::resnet",
                    "label": "Method",
                    "name": "ResNet",
                    "description": "Deep residual neural network",
                    "provenance": [{"page_numbers": [1, 2]}],
                }
            ],
            "relationships": [
                {
                    "source_id": "paper::resnet-doc",
                    "type": "USES_METHOD",
                    "target_id": "method::resnet",
                    "evidence": "We explicitly reformulate the layers as learning residual functions with reference to the layer inputs.",
                    "page_number": 2,
                }
            ],
        }
        json_file = settings.extracted_storage_dir / "resnet-doc.json"
        json_file.write_text(json.dumps(dummy_extraction), encoding="utf-8")

        # Create session
        created = client.post("/api/chats", json={"title": "New Research Chat", "doc_ids": ["resnet-doc"]}).json()
        session_id = created["id"]

        # Send message
        resp = client.post(
            f"/api/chats/{session_id}/messages",
            json={"content": "What is ResNet and how does residual learning work?"},
        )
        assert resp.status_code == 200
        data = resp.json()

        # Check user message
        assert data["user_message"]["role"] == "user"
        assert "residual learning" in data["user_message"]["content"]

        # Check assistant message
        assert data["assistant_message"]["role"] == "assistant"
        assert len(data["assistant_message"]["citations"]) > 0
        assert data["assistant_message"]["citations"][0]["doc_id"] == "resnet-doc"
        assert data["assistant_message"]["citations"][0]["filename"] == "deep_residual_learning.pdf"

        # Check session title was updated automatically from the first question
        assert data["session"]["title"].startswith("What is ResNet")

    def test_send_message_with_mocked_ollama_synthesis(self):
        # Create dummy extracted paper in isolated storage
        dummy_extraction = {
            "source_filename": "resnet.pdf",
            "doc_id": "resnet-doc-2",
            "summary": "Deep Residual Learning for Image Recognition.",
            "entities": [
                {
                    "canonical_id": "method::residual_connections",
                    "label": "Method",
                    "name": "Residual Connections",
                    "description": "Identity shortcut mappings",
                    "provenance": [{"page_numbers": [2]}],
                }
            ],
            "relationships": [],
        }
        json_file = settings.extracted_storage_dir / "resnet-doc-2.json"
        json_file.write_text(json.dumps(dummy_extraction), encoding="utf-8")

        created = client.post("/api/chats", json={"title": "LLM Test", "doc_ids": ["resnet-doc-2"]}).json()
        session_id = created["id"]

        with patch("app.services.graphrag_qa_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": {
                    "content": "According to the paper [resnet.pdf, p. 2], residual connections solve degradation.",
                }
            }
            mock_client.post.return_value = mock_resp

            resp = client.post(
                f"/api/chats/{session_id}/messages",
                json={"content": "How do residual connections address vanishing gradients?"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "According to the paper" in data["assistant_message"]["content"]

    def test_session_scoped_upload_and_documents_listing(self):
        # 1. Create two separate sessions
        session_a = client.post("/api/chats", json={"title": "Session A"}).json()
        session_b = client.post("/api/chats", json={"title": "Session B"}).json()

        pdf_bytes = (
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

        with patch("app.services.extraction_orchestrator.default_orchestrator.run_extraction"):
            upload_resp = client.post(
                "/api/upload",
                files=[("files", ("test_scoped.pdf", pdf_bytes, "application/pdf"))],
                data={"session_id": session_a["id"]},
            )
            assert upload_resp.status_code == 200
            up_data = upload_resp.json()
            assert up_data["session_id"] == session_a["id"]
            assert len(up_data["results"]) == 1
            doc_id = up_data["results"][0]["document_id"]
            assert doc_id is not None

        # Session A must now contain this doc_id
        session_a_detail = client.get(f"/api/chats/{session_a['id']}").json()
        assert doc_id in session_a_detail["doc_ids"]

        # Session B must NOT contain this doc_id
        session_b_detail = client.get(f"/api/chats/{session_b['id']}").json()
        assert doc_id not in session_b_detail["doc_ids"]

        # GET /api/documents?session_id=session_a must return only session_a's document
        docs_a = client.get(f"/api/documents?session_id={session_a['id']}").json()
        assert any(d["doc_id"] == doc_id for d in docs_a)

        # GET /api/documents?session_id=session_b must NOT return session_a's document
        docs_b = client.get(f"/api/documents?session_id={session_b['id']}").json()
        assert not any(d["doc_id"] == doc_id for d in docs_b)

    def test_empty_doc_ids_does_not_leak_other_chat_documents(self):
        # Create an extracted paper in storage belonging to another session
        secret_extraction = {
            "source_filename": "secret_quantum_paper.pdf",
            "doc_id": "secret-quantum-1",
            "summary": "Secret quantum algorithm achieves exponential speedup in teleportation.",
            "entities": [
                {
                    "canonical_id": "method::quantum_teleport",
                    "label": "Method",
                    "name": "Quantum Teleportation",
                    "description": "Exponential speedup teleportation protocol",
                    "provenance": [{"page_numbers": [1]}],
                }
            ],
            "relationships": [],
        }
        json_file = settings.extracted_storage_dir / "secret-quantum-1.json"
        json_file.write_text(json.dumps(secret_extraction), encoding="utf-8")

        # Session with empty doc_ids
        empty_session = client.post("/api/chats", json={"title": "Empty Session", "doc_ids": []}).json()

        # 1. Test with mocked Ollama: verify prompt sent to LLM never leaks secret paper
        with patch("app.services.graphrag_qa_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": {
                    "content": "No research papers are attached to this chat yet. Please attach a PDF using the paperclip.",
                }
            }
            mock_client.post.return_value = mock_resp

            resp = client.post(
                f"/api/chats/{empty_session['id']}/messages",
                json={"content": "What is the secret quantum teleportation algorithm speedup?"},
            )
            assert resp.status_code == 200
            data = resp.json()

            # Must NOT leak secret paper content or return citations
            assert "exponential speedup" not in data["assistant_message"]["content"].lower()
            assert len(data["assistant_message"]["citations"]) == 0
            assert "no research papers are attached" in data["assistant_message"]["content"].lower()

            # Verify that the prompt sent to Ollama did NOT contain the secret paper or its content (or short-circuited)
            if mock_client.post.call_args is not None:
                _, called_kwargs = mock_client.post.call_args
                sent_messages = called_kwargs.get("json", {}).get("messages", [])
                sent_text = json.dumps(sent_messages)
                assert "secret_quantum_paper.pdf" not in sent_text
                assert "exponential speedup" not in sent_text
                assert "secret-quantum-1" not in sent_text

        # 2. Test offline fallback: when Ollama is unavailable, fallback welcome message is returned
        with patch("app.services.graphrag_qa_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = Exception("Ollama offline")

            resp_offline = client.post(
                f"/api/chats/{empty_session['id']}/messages",
                json={"content": "Hello!"},
            )
            assert resp_offline.status_code == 200
            data_offline = resp_offline.json()
            assert "no research papers are attached" in data_offline["assistant_message"]["content"].lower()
            assert len(data_offline["assistant_message"]["citations"]) == 0

    def test_delete_chat_cleans_up_unreferenced_documents(self):
        # Setup session 1 with exclusive doc and shared doc
        doc_shared = "shared-doc-99"
        doc_exclusive = "exclusive-doc-88"

        session_1 = client.post("/api/chats", json={"title": "Session 1", "doc_ids": [doc_shared, doc_exclusive]}).json()
        session_2 = client.post("/api/chats", json={"title": "Session 2", "doc_ids": [doc_shared]}).json()

        # Create dummy artifacts
        (settings.upload_storage_dir / f"{doc_shared}.pdf").write_bytes(b"%PDF-1.4 shared")
        (settings.extracted_storage_dir / f"{doc_shared}.json").write_text("{}", encoding="utf-8")

        (settings.upload_storage_dir / f"{doc_exclusive}.pdf").write_bytes(b"%PDF-1.4 exclusive")
        (settings.extracted_storage_dir / f"{doc_exclusive}.json").write_text("{}", encoding="utf-8")

        # Delete session 1
        del_1 = client.delete(f"/api/chats/{session_1['id']}")
        assert del_1.status_code == 200

        # Exclusive doc must be deleted
        assert not (settings.upload_storage_dir / f"{doc_exclusive}.pdf").exists()
        assert not (settings.extracted_storage_dir / f"{doc_exclusive}.json").exists()

        # Shared doc must STILL exist because session_2 references it
        assert (settings.upload_storage_dir / f"{doc_shared}.pdf").exists()
        assert (settings.extracted_storage_dir / f"{doc_shared}.json").exists()

        # Delete session 2
        del_2 = client.delete(f"/api/chats/{session_2['id']}")
        assert del_2.status_code == 200

        # Shared doc must now be deleted
        assert not (settings.upload_storage_dir / f"{doc_shared}.pdf").exists()
        assert not (settings.extracted_storage_dir / f"{doc_shared}.json").exists()
