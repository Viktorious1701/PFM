"""Shared fixtures.

Constitution TST-07: SMTP is mocked by default. The one live-SMTP case is marked
`@pytest.mark.smtp` and excluded unless you ask for it.

Three seams make these tests deterministic without extra dependencies:
  * `clock.utcnow` is monkeypatched — the seam exists precisely so no `freezegun`
    is needed (plan.md A5, ADR-0004 rationale).
  * `RecordingEmailSender` captures messages instead of sending them.
  * The database is a fresh file-backed SQLite per test.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import security
from app.core.config import Settings, get_settings
from app.core.deps import get_db, get_email_sender
from app.db.base import Base
from app.main import create_app
from app.models.user import UserModel, UserRole, UserStatus
from app.services.email.sender import RecordingEmailSender

# A fixed instant so expiry assertions are exact rather than approximate
# (test_cases TC-23 requires `T + 24h` precisely).
FROZEN_NOW = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)

# >=32 bytes, per RFC 7518 §3.2 for HS256. A shorter key works but emits an
# InsecureKeyLengthWarning, and warning noise trains people to ignore warnings.
JWT_SECRET = "test-secret-not-a-real-key-padded-to-32-bytes-plus"
JWT_ALGORITHM = "HS256"


@pytest.fixture
def frozen_now(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Freeze the clock at FROZEN_NOW.

    Patches every module that imported `clock` by name. Patching
    `app.core.clock.utcnow` is enough because all of them call it through the
    module object rather than binding the function — which is the reason the
    seam is used that way.
    """
    monkeypatch.setattr("app.core.clock.utcnow", lambda: FROZEN_NOW)
    return FROZEN_NOW


@pytest.fixture
def advance_clock(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """Move the frozen clock forward. Used by TC-24 and TC-26's expired variant."""

    def _advance(delta: timedelta) -> datetime:
        moment = FROZEN_NOW + delta
        monkeypatch.setattr("app.core.clock.utcnow", lambda: moment)
        return moment

    return _advance


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Per-test settings pointing at an isolated database file.

    A file rather than `:memory:`: the app and the test share a session factory
    but not necessarily a connection, and an in-memory SQLite database is private
    to its connection.
    """
    return Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        jwt_secret=JWT_SECRET,
        jwt_ttl_minutes=60,
        invitation_ttl_hours=24,
        activation_url_template="http://testserver/activate?token={token}",
        smtp_user="",
        smtp_password="",
        email_send_mode="background",
    )


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    eng = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@pytest.fixture
def db(db_session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """A session for arranging fixtures and asserting persisted state."""
    session = db_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def email_sender() -> RecordingEmailSender:
    return RecordingEmailSender()


@pytest.fixture
def app(
    settings: Settings,
    db_session_factory: sessionmaker[Session],
    email_sender: RecordingEmailSender,
) -> FastAPI:
    """The real application, with only its edges replaced.

    Overridden: the database session, the settings, and the email sender.
    NOT overridden: the auth dependencies — `get_current_user` and
    `require_admin` run for real against real JWTs, which is what lets TC-11,
    TC-12 and TC-13 actually prove anything (SEC-07).
    """
    application = create_app(settings)

    def _get_db() -> Iterator[Session]:
        session = db_session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    application.dependency_overrides[get_db] = _get_db
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_email_sender] = lambda: email_sender
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """TestClient runs BackgroundTasks synchronously after the response.

    That is what makes TC-19 assertable: the background delivery failure has
    already happened by the time the response is inspected.
    """
    with TestClient(app) as test_client:
        yield test_client


# --- Users and tokens -----------------------------------------------------


def _make_user(
    db: Session,
    *,
    email: str,
    role: UserRole,
    status: UserStatus,
    password: str | None = "Str0ng-Passw0rd!",
) -> UserModel:
    user = UserModel(
        email=email,
        password_hash=security.hash_password(password) if password else None,
        full_name="Test User" if status is UserStatus.ACTIVE else None,
        status=status,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db: Session) -> UserModel:
    return _make_user(db, email="admin@example.com", role=UserRole.ADMIN, status=UserStatus.ACTIVE)


@pytest.fixture
def normal_user(db: Session) -> UserModel:
    return _make_user(db, email="member@example.com", role=UserRole.USER, status=UserStatus.ACTIVE)


def token_for(user: UserModel, settings: Settings) -> str:
    """Mint a bearer token directly.

    plan.md A11: `POST /api/v1/auth/login` belongs to SS-US-01 and is not built,
    so tests sign their own credential. The verification path under test is the
    real one — only the issuing step is short-circuited.
    """
    return security.encode_jwt(
        subject=user.id,
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
        algorithm=settings.jwt_algorithm,
    )


@pytest.fixture
def admin_headers(admin_user: UserModel, settings: Settings) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(admin_user, settings)}"}


@pytest.fixture
def user_headers(normal_user: UserModel, settings: Settings) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(normal_user, settings)}"}


# --- Live SMTP opt-in -----------------------------------------------------


def live_smtp_settings() -> Settings:
    """Settings read the normal way, for TC-22 only.

    Deliberately NOT the `settings` fixture above, which forces `smtp_user=""` so
    the rest of the suite can never send real mail.

    Reads through `Settings()` rather than `os.environ` directly, because `.env`
    is the documented place for credentials (SEC-09) and only pydantic-settings
    loads it. An earlier version checked `os.environ`, so filling in `.env` left
    TC-22 silently skipped while looking configured. pydantic-settings checks the
    real environment first and falls back to `.env`, so both routes now work.
    """
    return Settings()


def smtp_credentials_present() -> bool:
    return live_smtp_settings().smtp_configured
