"""Centralized configuration (pydantic-settings), overridable via environment variables.

All settings use the ``KB_`` env prefix, e.g. ``KB_CHUNK_MAX_CHARS=1500``. The deployment
node (Zeabur Arm Ampere A1) sets ``KB_DATA_DIR=/data`` to persist index/uploads/model cache on
the mounted volume; local development defaults to ``./data``.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KB_", env_file=".env", extra="ignore")

    # Models
    embedding_model: str = "BAAI/bge-m3"
    enable_ocr: bool = True

    # Chunking
    chunk_max_chars: int = 1200
    header_footer_min_repeats: int = 2

    # Retrieval
    rrf_k: int = 60
    top_k_default: int = 5

    # Limits
    max_upload_mb: int = 50

    # Persistence
    data_dir: str = "./data"
    chroma_collection: str = "knowledge"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
