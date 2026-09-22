"""create budgets table

BM-US-01 T-02 (spec BR-01, BR-05; plan.md T-01, T-02). One row per budget,
scoped to one wallet and one category — no `user_id` column at all (plan.md
A7); ownership is entirely transitive through `wallet_id`/`category_id`
(SRS §1.5; constitution SEC-08 extended one hop).

Index design (plan.md, constitution PF-02, SEC-08):

  ix_budgets_wallet_id     not unique — every ownership-scoped lookup this
                            story and future ones run against `budgets`
                            filters by `wallet_id`.
  ix_budgets_category_id   not unique — same rationale, for `category_id`.
  uq_budgets_wallet_category_period
                            composite unique constraint on
                            (wallet_id, category_id, period) — the database
                            backstop half of VL-05's two-level uniqueness
                            (plan.md A3, spec BR-05).

No `user_id` (plan.md A7), no `status` (plan.md A8), no `created_at`
(plan.md A11) — SDS §4.3.3's ERD lists `budgets` with exactly `id`,
`wallet_id`, `category_id`, `amount_limit`, `period`; adding a column the
ERD does not list is a domain-model change this story is not authorised to
make unilaterally.

`amount_limit` is `Numeric(15, 2)` — constitution VL-07, the same bound
`wallets.balance` uses.

Revision ID: 003e5ae90a36
Revises: 81bfb85427ed
Create Date: 2026-09-22 08:00:08.102468
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003e5ae90a36"
down_revision: str | None = "81bfb85427ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("wallet_id", sa.String(length=36), nullable=False),
        sa.Column("category_id", sa.String(length=36), nullable=False),
        sa.Column("amount_limit", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "wallet_id", "category_id", "period", name="uq_budgets_wallet_category_period"
        ),
    )
    # batch_alter_table because SQLite cannot ALTER most things in place
    # (render_as_batch=True in migrations/env.py).
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_budgets_wallet_id"), ["wallet_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_budgets_category_id"), ["category_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_budgets_category_id"))
        batch_op.drop_index(batch_op.f("ix_budgets_wallet_id"))

    op.drop_table("budgets")
