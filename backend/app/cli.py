"""Operator commands.

`create-admin` exists because registration is invitation-only: with no ACTIVE
user, nobody can authenticate to send the first invitation (spec Assumptions,
plan.md A10). This is the only path to the first account.

`mint-token` is a **development** helper. Issuing tokens is properly SS-US-01's
job via `POST /api/v1/auth/login`, which is not built (plan.md A11). Until it
exists, this is how you get a bearer token for Swagger and Postman.

Run with:
    uv run python -m app.cli create-admin --email you@example.com --password '…'
    uv run python -m app.cli mint-token --email you@example.com
"""

import argparse
import sys

from app.core import security
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.user import UserModel, UserRole, UserStatus
from app.repositories import user_repo


def create_admin(email: str, password: str, full_name: str | None) -> int:
    settings = get_settings()
    normalised = user_repo.normalize_email(email)

    try:
        password_hash = security.hash_password(password)
    except ValueError as exc:
        # VL-04: bcrypt truncates past 72 bytes rather than erroring, so this is
        # rejected at the boundary instead of silently shortening the password.
        print(f"error: {exc}", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        if user_repo.get_by_email(db, normalised) is not None:
            print(f"error: a user already exists for {normalised}", file=sys.stderr)
            return 1

        admin = UserModel(
            email=normalised,
            password_hash=password_hash,
            full_name=full_name,
            # ACTIVE and ADMIN directly — this is the bootstrap, so there is no
            # invitation to accept and no ADMIN to grant the role.
            status=UserStatus.ACTIVE,
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        print(f"created ADMIN {admin.email} (id={admin.id})")
        print(f"database: {settings.database_url}")
    return 0


def mint_token(email: str) -> int:
    """Print a bearer token for an existing ACTIVE user."""
    settings = get_settings()
    normalised = user_repo.normalize_email(email)

    with SessionLocal() as db:
        user = user_repo.get_by_email(db, normalised)
        if user is None:
            print(f"error: no user for {normalised}", file=sys.stderr)
            return 1
        if user.status is not UserStatus.ACTIVE:
            # Mirrors get_current_user: a non-ACTIVE account cannot act, so a
            # token for one would be rejected anyway (spec BR-06).
            print(
                f"error: {normalised} is {user.status} — only an ACTIVE user can hold a token",
                file=sys.stderr,
            )
            return 1

        token = security.encode_jwt(
            subject=user.id,
            role=user.role.value,
            secret=settings.jwt_secret,
            ttl_minutes=settings.jwt_ttl_minutes,
            algorithm=settings.jwt_algorithm,
        )

    print(token)
    print(
        f"\n# {user.role.value}, valid {settings.jwt_ttl_minutes} min. Use as:"
        f"\n#   Authorization: Bearer <token>",
        file=sys.stderr,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    admin = sub.add_parser("create-admin", help="Create the bootstrap ACTIVE ADMIN account.")
    admin.add_argument("--email", required=True)
    admin.add_argument("--password", required=True)
    admin.add_argument("--full-name", default=None)

    token = sub.add_parser("mint-token", help="Print a bearer token (dev only).")
    token.add_argument("--email", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "create-admin":
        return create_admin(args.email, args.password, args.full_name)
    if args.command == "mint-token":
        return mint_token(args.email)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
