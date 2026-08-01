"""Operator commands.

`create-admin` exists because registration is invitation-only: with no ACTIVE
user, nobody can authenticate to send the first invitation (spec Assumptions,
plan.md A10). This is the only path to the first account.

`mint-token` is a **development** helper. Issuing tokens is properly SS-US-01's
job via `POST /api/v1/auth/login`, which is not built (plan.md A11). Until it
exists, this is how you get a bearer token for Swagger and Postman.

`promote-admin` exists because `create-admin` refuses when the address already
has a row — which is exactly the state a real invited address ends up in
(PENDING, invited one or more times). Without this, an operator's own real
mailbox can never become the ADMIN once it has been invited even once (plan.md
UM-US-01 A12).

Run with:
    uv run python -m app.cli create-admin --email you@example.com --password '…'
    uv run python -m app.cli mint-token --email you@example.com
    uv run python -m app.cli promote-admin --email you@example.com --password '…'
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


def promote_admin(email: str, password: str, full_name: str | None) -> int:
    """Turn an existing user into an ACTIVE ADMIN, resetting its credential.

    Deliberately the opposite failure mode of `create_admin`: it requires the
    user to already exist and refuses if not — creating one from nothing is
    `create-admin`'s job. Overwriting the password is intentional: the
    operator running this owns the account and is choosing a fresh credential,
    not recovering a lost one.

    A stranded `PENDING` invitation for the address needs no cleanup: once
    this user is ACTIVE, that invitation's token is refused by
    `activation_service` as "not usable" (UM-US-02 EC-06), exactly the
    generic outcome any other stale token gets.
    """
    settings = get_settings()
    normalised = user_repo.normalize_email(email)

    try:
        password_hash = security.hash_password(password)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        user = user_repo.get_by_email(db, normalised)
        if user is None:
            print(
                f"error: no user for {normalised} — use create-admin to make one from nothing",
                file=sys.stderr,
            )
            return 1

        previous_status = user.status
        user.status = UserStatus.ACTIVE
        user.role = UserRole.ADMIN
        user.password_hash = password_hash
        if full_name is not None:
            user.full_name = full_name
        db.commit()
        db.refresh(user)

        print(f"promoted {user.email} to ACTIVE ADMIN (was {previous_status.value})")
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

    promote = sub.add_parser(
        "promote-admin", help="Turn an existing user into an ACTIVE ADMIN, resetting its password."
    )
    promote.add_argument("--email", required=True)
    promote.add_argument("--password", required=True)
    promote.add_argument("--full-name", default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "create-admin":
        return create_admin(args.email, args.password, args.full_name)
    if args.command == "mint-token":
        return mint_token(args.email)
    if args.command == "promote-admin":
        return promote_admin(args.email, args.password, args.full_name)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
