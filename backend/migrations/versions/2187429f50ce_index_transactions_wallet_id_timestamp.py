"""index transactions (wallet_id, timestamp)

TM-US-02 T-02 (plan.md A5, constitution PF-02). Every query this story
issues joins through `wallet_id` (A2) and orders by `timestamp` (A4); the
existing plain `ix_transactions_wallet_id` (TM-US-01) is a strict subset of
what this composite already provides, so it is dropped rather than kept
alongside the new one. `ix_transactions_category_id` is untouched — see A5
for why `category_id` does not get its own `timestamp` composite.

`TransactionModel.wallet_id` no longer carries `index=True` on its own —
`__table_args__` now declares the composite explicitly, by the same name
this migration creates, so the model and the real schema agree (no
autogenerate drift, unlike the pre-existing, separately-documented
`ix_users_created_at` case noted in `e33a7c97dab4`'s own docstring).

Revision ID: 2187429f50ce
Revises: e33a7c97dab4
Create Date: 2026-09-28 09:24:40.987816
"""

from collections.abc import Sequence

from alembic import op

revision: str = "2187429f50ce"
down_revision: str | None = "e33a7c97dab4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_transactions_wallet_id"))
        batch_op.create_index(
            batch_op.f("ix_transactions_wallet_id_timestamp"),
            ["wallet_id", "timestamp"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_transactions_wallet_id_timestamp"))
        batch_op.create_index(batch_op.f("ix_transactions_wallet_id"), ["wallet_id"], unique=False)
