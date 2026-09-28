"""create transactions table

TM-US-01 T-02 (spec BR-01, BR-05, BR-07; plan.md T-01, T-02). One row per
transaction, scoped to one wallet and one category — no `user_id` column at
all (plan.md A11), the same ownerless shape BM-US-01 established for
`budgets`; ownership is entirely transitive through `wallet_id`/
`category_id` (SRS §1.5; constitution SEC-08 extended one hop).

Index design (plan.md, constitution PF-02, SEC-08):

  ix_transactions_wallet_id     not unique — every ownership-scoped lookup
                                  this story and future ones run against
                                  `transactions` filters by `wallet_id`.
  ix_transactions_category_id   not unique — same rationale, for
                                  `category_id`.

No unique constraint of any kind (plan.md A15) — no AC, EC, or BR requires
transactions to be unique in any respect; this is the first money-bearing
story in this codebase where VL-05 does not apply.

No `user_id`, no `created_at` — SDS §4.3.3's ERD lists `transactions` with
exactly `id`, `wallet_id`, `category_id`, `amount`, `type`, `timestamp`,
`note`; adding a column the ERD does not list is a domain-model change this
story is not authorised to make unilaterally.

`amount` is `Numeric(15, 2)` — constitution VL-07, the same bound
`wallets.balance`/`budgets.amount_limit` use. `timestamp` is
`DateTime(timezone=True)` (plan.md A5) and carries no index this story —
TM-US-02 (list/filter, out of scope) is the story with an actual query to
justify one.

Autogenerate also proposed dropping `ix_users_created_at` on `users` here,
because `UserModel.created_at` does not currently carry `index=True` even
though migration `d01f2166c037_index_users_created_at.py` already created
that index. That drift predates this story, is unrelated to Transaction
Management, and is deliberately left untouched — this migration creates
`transactions` and nothing else.

Revision ID: e33a7c97dab4
Revises: 003e5ae90a36
Create Date: 2026-09-28 03:24:02.645135
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e33a7c97dab4"
down_revision: str | None = "003e5ae90a36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("wallet_id", sa.String(length=36), nullable=False),
        sa.Column("category_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column(
            "type",
            sa.Enum("INCOME", "EXPENSE", name="transactiontype", native_enum=False, length=10),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # batch_alter_table because SQLite cannot ALTER most things in place
    # (render_as_batch=True in migrations/env.py).
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_transactions_wallet_id"), ["wallet_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_transactions_category_id"), ["category_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_transactions_category_id"))
        batch_op.drop_index(batch_op.f("ix_transactions_wallet_id"))

    op.drop_table("transactions")
