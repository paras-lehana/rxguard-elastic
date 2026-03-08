"""
Application configuration — loaded from environment variables / .env file.

Usage:
    from app.config import get_settings
    settings = get_settings()
    print(settings.BEDROCK_KB_ID)
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration. All values are read from environment variables
    or a `.env` file in the project root.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── AWS Credentials ──────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"

    # ── Bedrock Knowledge Base ───────────────────────────────────────
    BEDROCK_KB_ID: str
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"

    # ── Kendra ───────────────────────────────────────────────────────
    KENDRA_INDEX_ID: Optional[str] = None  # Kendra GenAI Index ID
    KENDRA_INDEX_ARN: Optional[str] = None

    # ── Optional: Data Source ID (auto-detected if not set) ──────────
    BEDROCK_DATA_SOURCE_ID: Optional[str] = None

    # ── Soft-Delete Feature ──────────────────────────────────────────
    # When True, delete_document sets _is_active=false before hard-deleting.
    # This provides instant hiding from search while Kendra processes deletion.
    # Set to False if the _is_active custom attribute hasn't been registered in Kendra.
    ENABLE_SOFT_DELETE: bool = True

    # ── Server ───────────────────────────────────────────────────────
    PORT: int = 4101
    LOG_LEVEL: str = "INFO"

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "*"

    # ── Derived Properties ───────────────────────────────────────────
    @property
    def model_arn(self) -> str:
        """Full ARN for the Bedrock foundation model."""
        return f"arn:aws:bedrock:{self.AWS_REGION}::foundation-model/{self.BEDROCK_MODEL_ID}"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton settings instance — cached after first call.
    Call `get_settings.cache_clear()` in tests to reset.
    """
    return Settings()
