"""Settings, read from the environment.

Nothing here has a working default that reaches a third party. If a secret is
missing the application refuses to start rather than falling back to something
insecure, which is the mistake the previous build made with its operator login.
"""
from functools import lru_cache

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    debug: bool = False

    database_url: PostgresDsn = Field(
        ..., description="postgresql+psycopg://user:pass@host/db")
    redis_url: str = "redis://localhost:6379/0"

    # Auth. No default: an unset secret must stop the process, not silently
    # produce forgeable tokens.
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 12

    # De-duplication: reports of the same category in the same zone inside this
    # window are treated as one incident.
    dedup_window_seconds: int = 120
    # An unacknowledged P1 escalates after this long.
    escalation_seconds: int = 60

    # Photo storage. "local" writes to disk; "s3" targets any S3 compatible
    # service you host yourself, such as MinIO.
    storage_backend: str = "local"
    storage_local_path: str = "./var/uploads"
    s3_endpoint: str | None = None
    s3_bucket: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None

    # Triage. Every one of these is optional: with none configured the service
    # falls back to deterministic rules and says so, which is a supported mode
    # rather than a failure.
    severity_model_path: str | None = None      # trained classifier, Phase 2
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_base_url: str | None = None             # any OpenAI compatible endpoint
    llm_api_key: str | None = None
    llm_model: str | None = None

    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("jwt_secret")
    @classmethod
    def _reject_placeholder(cls, v: str) -> str:
        if v.lower() in {"change-me", "changeme", "secret", "development"}:
            raise ValueError("jwt_secret is still a placeholder; set a real one")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
