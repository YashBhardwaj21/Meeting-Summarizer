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
    storage_endpoint: str = "http://minio:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "meetings"
    storage_region: str = "us-east-1"

    # ── File limits ──────────────────────────────────────────────────
    max_file_size_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB
    presign_expiry_seconds: int = 900  # 15 minutes


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
