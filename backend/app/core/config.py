"""Application configuration module using Pydantic Settings."""

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
from pathlib import Path
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Central application settings validated at runtime."""

    # Project metadata
    PROJECT_NAME: str = "Scientific Paper Gap Finder"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Server binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS configuration
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return v if isinstance(v, list) else []

    # Database configuration
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/scientific_gap_finder"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "scientific_gap_finder"
    ALLOW_SQLITE_DEV_FALLBACK: bool = True
    SQLITE_FALLBACK_URL: str = "sqlite:///./data/metadata/gap_finder_dev.db"

    # LLM configuration (provider-independent abstraction)
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434/v1"
    DEFAULT_LLM_MODEL: str = "gemini-2.5-flash"

    # NLP & Storage settings (Phase 3 Semantic Representation)
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_DIMENSION: int = 384
    SPACY_MODEL: str = "en_core_web_sm"
    TOPIC_MODEL_ALGORITHM: str = "BERTopic"
    # Storage & Upload Configuration
    DATA_DIR: str = "./data"
    FAISS_INDEX_PATH: str = "./data/embeddings/faiss_index.bin"
    VECTOR_METADATA_PATH: str = "./data/embeddings/vector_metadata.json"
    METADATA_DIR: str = "./data/metadata"
    RAW_UPLOAD_DIR: str = "./data/raw"
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 Megabytes
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    ALLOWED_MIME_TYPES: List[str] = ["application/pdf", "application/x-pdf"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"

    model_config = SettingsConfigDict(
        env_file=(
            str(BASE_DIR / ".env"),
            str(BASE_DIR / "backend" / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
