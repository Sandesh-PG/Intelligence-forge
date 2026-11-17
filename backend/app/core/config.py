from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
STORAGE_BASE = BACKEND_ROOT / "storage"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server & CORS
    cors_origins: str = Field(default="http://localhost:3000")

    # Feature 01: Local Upload Storage
    upload_storage_dir: Path = Field(default_factory=lambda: STORAGE_BASE / "uploads")
    max_file_size_mb: int = Field(default=20, ge=1)
    max_batch_files: int = Field(default=3, ge=1)
    max_batch_size_mb: int = Field(default=60, ge=1)

    # Feature 02: Local Extraction (Docling + Ollama)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen2.5:3b")
    ollama_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    ollama_timeout_seconds: float = Field(default=120.0, gt=0.0)
    extraction_max_chunk_chars: int = Field(default=6000, ge=500)
    extracted_storage_dir: Path = Field(default_factory=lambda: STORAGE_BASE / "extracted")
    metadata_storage_path: Path = Field(default_factory=lambda: STORAGE_BASE / "metadata.json")
    # Feature 03: Neo4j Graph Persistence Settings
    neo4j_uri: str = Field(default="", description="Bolt/Aura connection URI")
    neo4j_username: str = Field(default="neo4j", description="Database username")
    neo4j_password: str = Field(default="", description="Database password")
    neo4j_database: str = Field(default="neo4j", description="Target Neo4j database name")
    neo4j_auto_sync: bool = Field(default=True, description="Auto sync after extraction")
    neo4j_timeout_seconds: int = Field(default=30, description="Connection and transaction timeout")

    # Feature 05: Chat & Sessions Persistence
    data_dir: Path = Field(default_factory=lambda: BACKEND_ROOT / "data")

    # Feature 07: Vector Embeddings & Dual-Agent Web Search
    embedding_model: str = Field(default="nomic-embed-text")
    enable_global_web_agent: bool = Field(default=True)
    web_search_timeout: float = Field(default=8.0)

    @field_validator("upload_storage_dir", "extracted_storage_dir", "metadata_storage_path", "data_dir", mode="after")
    @classmethod
    def anchor_storage_path(cls, v: Path) -> Path:
        if not v.is_absolute():
            v_str = str(v).replace("\\", "/")
            if v_str.startswith("backend/storage/"):
                subpath = v_str[len("backend/storage/"):]
                return (STORAGE_BASE / subpath).resolve()
            elif v_str.startswith("storage/"):
                subpath = v_str[len("storage/"):]
                return (STORAGE_BASE / subpath).resolve()
            elif v_str.startswith("backend/data/"):
                subpath = v_str[len("backend/data/"):]
                return (BACKEND_ROOT / "data" / subpath).resolve()
            elif v_str.startswith("data/"):
                subpath = v_str[len("data/"):]
                return (BACKEND_ROOT / "data" / subpath).resolve()
            return (STORAGE_BASE / v).resolve()
        return v

    def ensure_storage_dirs(self) -> None:
        self.upload_storage_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()