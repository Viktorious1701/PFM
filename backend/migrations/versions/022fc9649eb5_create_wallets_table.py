"""create wallets table

WM-US-01 T-02 (spec BR-01; plan.md T-01, T-02). One row per wallet, owned by
exactly one user (SRS §1.5 "User owns Wallet"; constitution SEC-08).

Index design (plan.md, constitution PF-02, SEC-08):

  ix_wallets_user_id   not unique — every future query on this table filters
                        by owner, so the FK is indexed now even though this
                        story only ever writes one row per request.

No `created_at` column (plan.md A5) — SDS §4.3.3's ERD lists `wallets` with
exactly `id`, `user_id`, `name`, `type`, `balance`, `currency`; a timestamp
column would be a domain-model change this story is not authorised to make
unilaterally.

`balance` is `Numeric(15, 2)` — constitution VL-07, first table in this
codebase to store money.

Revision ID: 022fc9649eb5
Revises: d01f2166c037
Create Date: 2026-09-03 10:28:34.557805
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "022fc9649eb5"
down_revision: str | None = "d01f2166c037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("balance", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # batch_alter_table because SQLite cannot ALTER most things in place
    # (render_as_batch=True in migrations/env.py).
    with op.batch_alter_table("wallets", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_wallets_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("wallets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_wallets_user_id"))

    op.drop_table("wallets")
