"""Unit tests for the operator CLI.

`create-admin` closes the invite-only bootstrap cycle (plan.md A10): with no
ACTIVE user, nobody can authenticate to send the first invitation. If it is
broken, the whole feature is unreachable — so it is worth real tests.

Supporting coverage, not test_cases.md TCs.
"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import security
from app.db.base import Base
from app.models.user import UserRole, UserStatus
from app.repositories import user_repo


@pytest.fixture
def cli_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    """Point the CLI's module-level SessionLocal at a throwaway database."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'cli.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    monkeypatch.setattr("app.cli.SessionLocal", factory)
    return factory


def test_create_admin_writes_an_active_admin_with_a_hashed_password(
    cli_db: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    from app.cli import main

    exit_code = main(
        ["create-admin", "--email", "Boss@Example.COM", "--password", "Str0ng-Passw0rd!"]
    )

    assert exit_code == 0
    with cli_db() as db:
        # Normalised on the way in, like every other write (FR-03).
        admin = user_repo.get_by_email(db, "boss@example.com")
        assert admin is not None
        assert admin.status is UserStatus.ACTIVE
        assert admin.role is UserRole.ADMIN
        assert admin.password_hash is not None
        assert security.verify_password("Str0ng-Passw0rd!", admin.password_hash)
        # SEC-01: the hash is never printed.
        assert admin.password_hash not in capsys.readouterr().out


def test_create_admin_refuses_a_duplicate_address(cli_db: sessionmaker[Session]) -> None:
    from app.cli import main

    args = ["create-admin", "--email", "boss@example.com", "--password", "Str0ng-Passw0rd!"]
    assert main(args) == 0
    assert main(args) == 1


def test_create_admin_refuses_a_password_past_bcrypts_ceiling(
    cli_db: sessionmaker[Session],
) -> None:
    """VL-04 — refused rather than silently truncated to 72 bytes."""
    from app.cli import main

    exit_code = main(["create-admin", "--email", "boss@example.com", "--password", "a" * 100])

    assert exit_code == 2
    with cli_db() as db:
        assert user_repo.get_by_email(db, "boss@example.com") is None


def test_mint_token_prints_a_token_the_app_will_accept(
    cli_db: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    """plan.md A11: stands in for POST /auth/login, which SS-US-01 will deliver."""
    from app.cli import main
    from app.core.config import get_settings

    main(["create-admin", "--email", "boss@example.com", "--password", "Str0ng-Passw0rd!"])
    capsys.readouterr()

    assert main(["mint-token", "--email", "boss@example.com"]) == 0

    token = capsys.readouterr().out.strip()
    settings = get_settings()
    payload = security.decode_jwt(token, settings.jwt_secret, settings.jwt_algorithm)

    with cli_db() as db:
        admin = user_repo.get_by_email(db, "boss@example.com")
        assert admin is not None
        assert payload["sub"] == admin.id
    assert payload["role"] == "ADMIN"


def test_mint_token_refuses_an_unknown_address(cli_db: sessionmaker[Session]) -> None:
    from app.cli import main

    assert main(["mint-token", "--email", "nobody@example.com"]) == 1


def test_mint_token_refuses_a_non_active_account(cli_db: sessionmaker[Session]) -> None:
    """Mirrors get_current_user: a PENDING account cannot act (spec BR-06)."""
    from app.cli import main

    with cli_db() as db:
        user_repo.add_pending_user(db, "invited@example.com")
        db.commit()

    assert main(["mint-token", "--email", "invited@example.com"]) == 1


def test_an_unknown_command_is_a_usage_error() -> None:
    from app.cli import main

    with pytest.raises(SystemExit):
        main(["no-such-command"])
