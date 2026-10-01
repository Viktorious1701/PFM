"""index budgets period

BM-US-02 T-02 (plan.md A6, A13; constitution PF-02). `budget_repo.list_owned()`
filters `budgets.period == :period` directly in a WHERE clause for the first
time anywhere in this codebase -- the existing composite
`uq_budgets_wallet_category_period` has `period` only as its third column,
which does not efficiently serve a query that supplies `wallet_id` only
through a join to `wallets` and supplies no `category_id` predicate at all.

`BudgetModel.period` now also carries `index=True` on its own `mapped_column`
(plan.md A13) so a future `alembic revision --autogenerate` agrees with the
real schema instead of proposing to drop this index.

Revision ID: f3a9c1d4e8b2
Revises: 2187429f50ce
Create Date: 2026-10-01 02:56:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f3a9c1d4e8b2"
down_revision: str | None = "2187429f50ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_budgets_period"), ["period"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_budgets_period"))
