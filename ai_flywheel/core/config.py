"""Platform Core — configuration management via Pydantic BaseSettings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global platform settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: str = "development"
    log_level: str = "DEBUG"

    # Database
    database_url: str = "postgresql+asyncpg://flywheel:flywheel_dev@localhost:5432/ai_flywheel"
    database_url_sync: str = "postgresql://flywheel:flywheel_dev@localhost:5432/ai_flywheel"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "ai-flywheel-main"

    # LLM Providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Auth (Clerk)
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_jwks_url: str = ""

    # Object Storage
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "ai-flywheel"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


# Singleton — import this everywhere
settings = Settings()
