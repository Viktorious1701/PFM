"""Application settings (SDS §7.5, §9.4 — pydantic-settings from an isolated .env).

Deliberately minimal. Each story adds only the settings its spec justifies —
JWT with US-02-01, invitation TTL and SMTP with US-01-01, and so on. Settings
that exist before a requirement asks for them are speculation.

Constitution: SEC-09, ENV-01.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PFM API"
    environment: str = "development"

    # API-01: every route lives under this prefix.
    api_v1_prefix: str = "/api/v1"

    # ENV-03: SQLite locally, PostgreSQL in deployment (SDS §4.5).
    database_url: str = "sqlite:///./pfm.db"


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is parsed once per process."""
    return Settings()
