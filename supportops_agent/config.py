"""Configuration management using Pydantic Settings."""

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Gemini API
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash-lite"  # Using Gemini 2.0 Flash Experimental
    gemini_base_url: Optional[str] = None

    # Database (use SQLite by default for local development)
    database_url: str = "sqlite:///./supportops.db"

    # Observability
    otel_exporter_otlp_endpoint: Optional[str] = None
    otel_service_name: str = "supportops-agent"

    # Security
    store_raw: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
