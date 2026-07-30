"""Shared fixtures.

Design notes:
* Each test gets a fresh in-memory SQLite database (StaticPool so every
  connection sees the same one), created from the ORM metadata for speed.
  `tests/integration/test_migrations.py` separately proves the Alembic
  migrations produce that same schema, so the shortcut here is safe.
* The email sender is replaced by a recorder, which is how AC-5 is asserted
  without touching Gmail.
* Time is controlled by monkeypatching `app.core.clock.utcnow` — the single seam
  every TTL decision reads.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import clock
from app.core.config import Settings
from app.core.deps import get_email_sender
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import User, UserStatus
from app.services.email.sender import EmailMessage


class RecordingEmailSender:
    """Test double for EmailSender. Optionally explodes, to exercise failure paths."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []
        self.fail_with: Exception | None = None

    def send(self, message: EmailMessage) -> None:
        if self.fail_with is not None:
            raise self.fail_with
        self.sent.append(message)

    @property
    def last(self) -> EmailMessage:
        assert self.sent, "no email was sent"
        return self.sent[-1]

    def activation_url(self) -> str:
        """Pull the activation link back out of the email body, the way a
        recipient would — this is what makes AC-5 a real assertion."""
        import re

        match = re.search(r"https?://\S*?token=([A-Za-z0-9_\-]+)", self.last.text_body)
        assert match, f"no activation URL in email body:\n{self.last.text_body}"
        return match.group(0)

    def token(self) -> str:
        return self.activation_url().split("token=", 1)[1]


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite://",
        jwt_secret="test-secret",
        jwt_ttl_minutes=60,
        invitation_ttl_hours=24,
        activation_url_template="https://pfm.test/activate?token={token}",
        smtp_user="test@example.com",
        smtp_password="app-password",
        email_send_mode="background",
    )


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def email_sender() -> RecordingEmailSender:
    return RecordingEmailSender()


@pytest.fixture
def client(
    settings: Settings, db_session: Session, email_sender: RecordingEmailSender
) -> Iterator[TestClient]:
    app = create_app(settings)

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_email_sender] = lambda: email_sender
    # create_app captured `settings` directly, but the DI graph resolves it via
    # get_settings, so that has to be overridden too.
    from app.core.config import get_settings

    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# --- user factories -------------------------------------------------------


@pytest.fixture
def active_user(db_session: Session) -> User:
    user = User(
        email="admin@family.test",
        full_name="Family Admin",
        password_hash=hash_password("adminpass123"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(client: TestClient, active_user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": active_user.email, "password": "adminpass123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- time control ---------------------------------------------------------


@pytest.fixture
def freeze_time(monkeypatch: pytest.MonkeyPatch):
    """Pin utcnow(), then optionally advance it.

        now = freeze_time(datetime(2026, 1, 1, tzinfo=UTC))
        now.advance(hours=25)
    """

    class Controller:
        def __init__(self, start: datetime) -> None:
            self.current = start
            self._apply()

        def _apply(self) -> None:
            monkeypatch.setattr(clock, "utcnow", lambda: self.current)
            # Modules that did `from app.core.clock import utcnow` hold their own
            # reference, so patch those bindings too.
            for module in (
                "app.core.security",
                "app.services.invitation_service",
                "app.services.activation_service",
                "app.models.user",
            ):
                monkeypatch.setattr(f"{module}.utcnow", lambda: self.current, raising=False)

        def advance(self, **delta: float) -> datetime:
            self.current = self.current + timedelta(**delta)
            self._apply()
            return self.current

    def _freeze(start: datetime | None = None) -> Controller:
        return Controller(start or datetime(2026, 7, 30, 12, 0, tzinfo=UTC))

    return _freeze
