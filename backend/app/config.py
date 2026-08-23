"""Application configuration via pydantic-settings."""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application settings, loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = "Meeting Summarizer"
    debug: bool = False
    cors_origins: str = '["http://localhost:3000"]'

    @property
    def cors_origin_list(self) -> list[str]:
        return json.loads(self.cors_origins)

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@db:5432/meeting_summarizer"
    )

    # ── Redis ────────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── Object Storage (MinIO locally, R2 in production) ─────────────
    storage_internal_endpoint: str = "http://minio:9000"
    storage_public_endpoint: str = "http://localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "meetings"
    storage_region: str = "us-east-1"

    # ── File limits ──────────────────────────────────────────────────
    max_file_size_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB
    presign_expiry_seconds: int = 900  # 15 minutes
    storage_quota_bytes: int = 10 * 1024 * 1024 * 1024  # 10 GB

    # ── ASR ──────────────────────────────────────────────────────────
    groq_api_key: str = ""
    asr_provider: str = "local"
    asr_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    asr_chunk_duration_seconds: int = 600
    asr_chunk_overlap_seconds: int = 5
    asr_concurrency: int = 1
    asr_timeout_seconds: int = 120
    asr_max_retries: int = 3

    # ── Diarization ──────────────────────────────────────────────────
    diarization_enabled: bool = True
    diarization_model: str = "pyannote/speaker-diarization-community-1"
    hf_token: str = ""

    # ── Embeddings ───────────────────────────────────────────────────
    openai_api_key: str = ""
    embedding_provider: str = "nomic"
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768
    embedding_batch_size: int = 32
    embedding_timeout_seconds: int = 60
    embedding_max_retries: int = 3
    embedding_max_input_tokens: int = 8191

    # ── LLM ──────────────────────────────────────────────────────────
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://host.docker.internal:11434"
    llm_model: str = "gemma3:4b"
    llm_temperature: float = 0.2
    llm_timeout_seconds: int = 120
    rag_top_k: int = 8
    rag_similarity_threshold: float = 0.6
    chat_history_turns: int = 6

    # ── Chunking ─────────────────────────────────────────────────────
    transcript_chunk_max_tokens: int = 800
    transcript_chunk_overlap_tokens: int = 80
    tokenizer_encoding: str = "cl100k_base"

    # ── Worker / Resources ───────────────────────────────────────────
    media_temp_dir: str = "/tmp/meeting-summarizer"
    processing_max_attempts: int = 3
    processing_job_timeout_seconds: int = 10800
    max_media_duration_seconds: int = 7200       # 2 hours
    max_temp_storage_bytes: int = 5_368_709_120  # 5 GB

    # ── Pipeline Versioning ──────────────────────────────────────────
    processing_pipeline_version: str = "2.0"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
