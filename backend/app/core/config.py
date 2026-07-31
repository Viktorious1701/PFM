"""Application settings (SDS §7.5, §9.4 — pydantic-settings from an isolated .env).

Deliberately minimal. Each story adds only the settings its spec justifies —
JWT with US-02-01, invitation TTL and SMTP with US-01-01, and so on. Settings
that exist before a requirement asks for them are speculation.

Constitution: SEC-09, ENV-01.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

EmailSendMode = Literal["background", "sync"]


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

    # --- Auth (SEC-06) ----------------------------------------------------
    # HS256 with a 60-minute access token. The login endpoint that issues these
    # belongs to SS-US-01; UM-US-01 only *verifies* them (plan.md A11).
    # >=32 bytes, per RFC 7518 §3.2 for HS256 — a shorter key is accepted but
    # warned about. Obviously a placeholder: .env supplies the real one (SEC-09).
    jwt_secret: str = "dev-only-change-me-not-a-real-secret-key-32b+"
    jwt_ttl_minutes: int = 60
    jwt_algorithm: str = "HS256"

    # --- Invitations (US-01-01) -------------------------------------------
    # spec FR-09 / AC-06: expiry is exactly this many hours after creation.
    invitation_ttl_hours: int = 24

    # `{token}` is substituted with the raw invitation token. That raw value
    # exists only here and in the delivered email (spec BR-07).
    activation_url_template: str = "http://localhost:8000/activate?token={token}"

    # spec EC-04, test_cases QF-08: inclusive maximum, so 321 characters is
    # rejected. RFC 5321 caps a path at 256; 320 is the project's chosen bound.
    max_email_length: int = 320

    # --- Gmail SMTP (SDS §13) --------------------------------------------
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "PFM <no-reply@example.com>"

    # plan.md A4 — "background" keeps mail off the request path so FR-19 /
    # NFR-01's 300 ms p95 holds. "sync" sends inline and surfaces a 502 on
    # failure (spec FR-20, EC-07); intended for first-time Gmail wiring.
    email_send_mode: EmailSendMode = "background"

    @property
    def smtp_configured(self) -> bool:
        """EC-07: no credentials means delivery cannot succeed, and must not pretend to."""
        return bool(self.smtp_user and self.smtp_password)


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is parsed once per process."""
    return Settings()
