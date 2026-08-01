"""GET /api/v1/dev/outbox (UM-US-01 A13/A14).

Not a test_cases.md TC — this route belongs to no SRS/SDS story, it is
operational tooling recorded directly in specs/001-user-onboarding/plan.md's
Gaps & Decisions. Builds its own app/client per test, rather than reusing
conftest.py's shared `settings` fixture, because these tests need to vary
`environment` and `email_transport` — the one thing the shared fixture
deliberately holds fixed.
"""

from collections.abc import Iterator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import security
from app.core.config import Settings, get_settings
from app.core.deps import get_db
from app.db.base import Base
from app.main import create_app
from app.models.user import UserModel, UserRole, UserStatus

INVITE_URL = "/api/v1/users/invite"
OUTBOX_URL = "/api/v1/dev/outbox"

JWT_SECRET = "test-secret-not-a-real-key-padded-to-32-bytes-plus"


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    kwargs: dict[str, object] = {
        "environment": "test",
        "database_url": f"sqlite:///{tmp_path / 'test.db'}",
        "jwt_secret": JWT_SECRET,
        "activation_url_template": "http://testserver/activate?token={token}",
        "smtp_user": "",
        "smtp_password": "",
        "outbox_dir": tmp_path / "outbox",
    }
    kwargs.update(overrides)
    return Settings(**kwargs)  # type: ignore[arg-type]


def _client(settings: Settings) -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

    application = create_app(settings)

    def _get_db() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = _get_db
    application.dependency_overrides[get_settings] = lambda: settings
    return TestClient(application), factory


def _make_user_and_token(
    db_factory: sessionmaker[Session], settings: Settings, *, role: UserRole
) -> str:
    with db_factory() as db:
        user = UserModel(
            email=f"{role.value.lower()}@example.com",
            password_hash=security.hash_password("Str0ng-Passw0rd!"),
            full_name=role.value.title(),
            status=UserStatus.ACTIVE,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    return security.encode_jwt(
        subject=user_id,
        role=role.value,
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
        algorithm=settings.jwt_algorithm,
    )


def test_outbox_lists_a_message_written_by_the_file_transport(tmp_path: Path) -> None:
    settings = _settings(tmp_path, email_transport="outbox", email_send_mode="sync")
    client, db_factory = _client(settings)
    token = _make_user_and_token(db_factory, settings, role=UserRole.ADMIN)
    headers = {"Authorization": f"Bearer {token}"}

    invite_response = client.post(
        INVITE_URL, json={"email": "invitee@example.com"}, headers=headers
    )
    assert invite_response.status_code == 201

    response = client.get(OUTBOX_URL, headers=headers)

    assert response.status_code == 200
    messages = response.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["to"] == "invitee@example.com"
    assert messages[0]["activation_url"] is not None
    assert "token=" in messages[0]["activation_url"]


def test_outbox_returns_an_empty_list_when_nothing_has_been_sent(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    client, db_factory = _client(settings)
    token = _make_user_and_token(db_factory, settings, role=UserRole.ADMIN)

    response = client.get(OUTBOX_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["messages"] == []


def test_outbox_requires_admin_role(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    client, db_factory = _client(settings)
    token = _make_user_and_token(db_factory, settings, role=UserRole.USER)

    response = client.get(OUTBOX_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_outbox_requires_authentication(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    client, _ = _client(settings)

    response = client.get(OUTBOX_URL)

    assert response.status_code == 401


def test_outbox_404s_in_production_even_for_an_admin(tmp_path: Path) -> None:
    settings = _settings(tmp_path, environment="production")
    client, db_factory = _client(settings)
    token = _make_user_and_token(db_factory, settings, role=UserRole.ADMIN)

    response = client.get(OUTBOX_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
