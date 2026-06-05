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
    database_url: str = "postgresql+asyncpg://flywheel:flywheel_dev@localhost:5433/ai_flywheel"
    database_url_sync: str = "postgresql://flywheel:flywheel_dev@localhost:5433/ai_flywheel"

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

    # Auth (JWT)
    jwt_secret_key: str = "dev-secret-key-change-in-production-abc123xyz"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Slack Integration
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_app_token: str = ""
    slack_channel: str = ""  # Default channel for notifications

    # RunCord (Builder Engine)
    runcord_api_key: str = ""
    runcord_base_url: str = "https://api.runcord.com/api/v1"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


# Singleton — import this everywhere
settings = Settings()
