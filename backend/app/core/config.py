from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
STORAGE_BASE = BACKEND_ROOT / "storage"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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

    @field_validator("upload_storage_dir", "extracted_storage_dir", "metadata_storage_path", mode="after")
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
            return (STORAGE_BASE / v).resolve()
        return v

    def ensure_storage_dirs(self) -> None:
        self.upload_storage_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_storage_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()