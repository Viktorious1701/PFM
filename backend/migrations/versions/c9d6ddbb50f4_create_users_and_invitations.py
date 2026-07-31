"""create users and invitations

Both tables in one revision, because inviting writes to both inside a single
transaction and neither is meaningful alone (spec BR-08, plan.md A1). DOD-02.

Index design is load-bearing, not incidental (plan.md A7, constitution PF-02):

  ix_users_email            UNIQUE  — uniqueness lives on the *account*. Second
                                      line of defence behind the service check,
                                      so a concurrent duplicate becomes a 409
                                      rather than two accounts (spec EC-05, VL-05).
  ix_invitations_email      not unique — an address may be invited many times;
                                      history of attempts is why this entity is
                                      separate (spec EC-02/EC-03, FR-11).
  ix_invitations_token_hash UNIQUE  — the activation lookup key, and it backstops
                                      token uniqueness (spec AC-06, FR-08).

Only the SHA-256 digest of a token is stored; the raw value exists solely in the
delivered email (spec BR-07, SEC-03, plan.md A2).

Revision ID: c9d6ddbb50f4
Revises:
Create Date: 2026-07-31 02:43:49.122672
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d6ddbb50f4"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        # Both nullable: an invited account holds no credentials until it is
        # activated (spec AC-07, FR-05, BR-06).
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        # native_enum=False stores the literal as text, which keeps the same DDL
        # working on SQLite and PostgreSQL (ENV-03) and matches NC-05's wire
        # values exactly.
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "ACTIVE", "DEACTIVATED", name="userstatus", native_enum=False, length=20
            ),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "USER", name="userrole", native_enum=False, length=10),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # batch_alter_table because SQLite cannot ALTER most things in place
    # (render_as_batch=True in migrations/env.py).
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)

    op.create_table(
        "invitations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        # EXPIRED is present for readers to derive, never written by a writer —
        # there is no sweeper job (spec BR-04, plan.md A5).
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "ACCEPTED",
                "EXPIRED",
                "SUPERSEDED",
                name="invitationstatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        # spec FR-07: which ADMIN issued this invitation.
        sa.Column("invited_by_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("invitations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_invitations_email"), ["email"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_invitations_invited_by_id"), ["invited_by_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_invitations_token_hash"), ["token_hash"], unique=True)


def downgrade() -> None:
    # invitations first — it carries the FK to users.
    with op.batch_alter_table("invitations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_invitations_token_hash"))
        batch_op.drop_index(batch_op.f("ix_invitations_invited_by_id"))
        batch_op.drop_index(batch_op.f("ix_invitations_email"))

    op.drop_table("invitations")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email"))

    op.drop_table("users")
