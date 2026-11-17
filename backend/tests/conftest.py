import os
os.environ["NEO4J_URI"] = ""
os.environ["ENABLE_GLOBAL_WEB_AGENT"] = "false"

import pytest
from app.core.config import settings
settings.neo4j_uri = ""
settings.enable_global_web_agent = False
from app.services.chat_store import chat_store
from app.services.extraction_orchestrator import ExtractionMetadataStore, default_orchestrator
from app.services.storage import _metadata_store


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """
    Autouse fixture that isolates filesystem storage, in-memory metadata,
    and chat database into pytest tmp_path to prevent live data pollution
    and sandbox network hangs during test runs.
    """
    test_upload_dir = tmp_path / "uploads"
    test_extracted_dir = tmp_path / "extracted"
    test_metadata_path = tmp_path / "metadata.json"
    test_data_dir = tmp_path / "data"

    test_upload_dir.mkdir(parents=True, exist_ok=True)
    test_extracted_dir.mkdir(parents=True, exist_ok=True)
    test_data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "upload_storage_dir", test_upload_dir)
    monkeypatch.setattr(settings, "extracted_storage_dir", test_extracted_dir)
    monkeypatch.setattr(settings, "metadata_storage_path", test_metadata_path)
    monkeypatch.setattr(settings, "data_dir", test_data_dir)
    monkeypatch.setattr(settings, "neo4j_uri", "")
    monkeypatch.setattr(settings, "enable_global_web_agent", False)
    monkeypatch.setattr("app.services.embedding_service._ollama_embed_available", False)

    default_orchestrator.upload_dir = test_upload_dir
    default_orchestrator.extracted_dir = test_extracted_dir
    default_orchestrator.metadata_store = ExtractionMetadataStore(test_metadata_path)

    chat_store.init_db()
    _metadata_store.clear()

    yield
