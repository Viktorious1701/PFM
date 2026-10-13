"""add archived_at to categories

CM-US-05 T-01 (plan.md A1, A12). Soft-delete marker for archiving a category:
`NULL` means active, a non-NULL value means archived and records the moment
(spec AC-01/AC-05/FR-04/FR-05). Nullable, no default -- every category this
codebase has already created has no value for it, and the column's own
absence of a default is what lets `category_repo.archive_category()` test
`IS NULL` as the idempotency guard (A6). Mirrors
`b4f1e7a2c6d9_add_archived_at_to_wallets.py` exactly, adapted to `categories`.

No dedicated index on `archived_at` alone -- `category_repo.list_owned()`'s
new predicate always runs alongside the already-indexed `user_id` equality
filter (A12).

batch_alter_table because SQLite cannot ALTER most things in place
(render_as_batch=True in migrations/env.py), matching every other
column/index change in this codebase.

Revision ID: e7a1c3f9b2d4
Revises: b4f1e7a2c6d9
Create Date: 2026-10-09 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7a1c3f9b2d4"
down_revision: str | None = "b4f1e7a2c6d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.drop_column("archived_at")
