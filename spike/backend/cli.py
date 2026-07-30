"""Operational commands.

`create-admin` exists because registration is invite-only: without a first ACTIVE
account, nobody can authenticate to call US-01-01, so no invitation can ever be
sent. This is the bootstrap that breaks that cycle.

    uv run python -m app.cli create-admin --email you@example.com --password 'secret123'
"""

import argparse
import sys

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserStatus
from app.repositories import user_repo


def create_admin(email: str, password: str, full_name: str | None) -> int:
    settings = get_settings()
    if len(password) < settings.password_min_length:
        print(
            f"error: password must be at least {settings.password_min_length} characters",
            file=sys.stderr,
        )
        return 2

    with SessionLocal() as db:
        existing = user_repo.get_by_email(db, email)
        if existing is not None:
            if existing.status is UserStatus.ACTIVE:
                print(f"error: {existing.email} is already an ACTIVE account", file=sys.stderr)
                return 1
            # Promote a pending invitation straight to active.
            existing.full_name = full_name or existing.full_name or email.split("@")[0]
            existing.password_hash = hash_password(password)
            existing.status = UserStatus.ACTIVE
            existing.invitation_token_hash = None
            existing.token_expires_at = None
            db.commit()
            print(f"promoted pending user to ACTIVE: {existing.email} ({existing.id})")
            return 0

        user = User(
            email=user_repo.normalize_email(email),
            full_name=full_name or email.split("@")[0],
            password_hash=hash_password(password),
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        print(f"created ACTIVE user: {user.email} ({user.id})")
        return 0


def list_users_cmd() -> int:
    with SessionLocal() as db:
        users = user_repo.list_users(db)
        if not users:
            print("(no users)")
            return 0
        print(f"{'STATUS':<8}  {'EMAIL':<32}  {'NAME':<20}  CREATED")
        for u in users:
            name = u.full_name or "-"
            print(f"{u.status.value:<8}  {u.email:<32}  {name:<20}  {u.created_at:%Y-%m-%d %H:%M}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="PFM backend operations")
    sub = parser.add_subparsers(dest="command", required=True)

    admin = sub.add_parser("create-admin", help="Create (or promote) the bootstrap ACTIVE user")
    admin.add_argument("--email", required=True)
    admin.add_argument("--password", required=True)
    admin.add_argument("--full-name", default=None)

    sub.add_parser("list-users", help="Print all users and their status")

    args = parser.parse_args(argv)

    if args.command == "create-admin":
        return create_admin(args.email, args.password, args.full_name)
    if args.command == "list-users":
        return list_users_cmd()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
