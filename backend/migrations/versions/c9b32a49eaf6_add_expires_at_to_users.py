"""add expires_at to users

SS-US-03 T-01 (plan.md A1). The guest trial's end: a nullable, timezone-aware
`users.expires_at`. `NULL` for every member — no backfill, every row this
codebase has already created is a member. Set only on a `GUEST` row, to the
moment its 7-day trial ends (spec BR-01).

Indexed because both the purge (`expires_at <= now`) and the live-trial cap
filter on it (constitution PF-02).

`UserRole.GUEST` needs no schema change: `users.role` is a `VARCHAR(10)` with
no `CHECK` constraint (`c9d6ddbb50f4` creates none), so `"GUEST"` fits as a
new enum member only (A1).

batch_alter_table because SQLite cannot ALTER most things in place
(render_as_batch=True in migrations/env.py), matching
`e7a1c3f9b2d4_add_archived_at_to_categories.py`'s add-column pattern and
`d01f2166c037_index_users_created_at.py`'s index pattern.

Revision ID: c9b32a49eaf6
Revises: e7a1c3f9b2d4
Create Date: 2026-10-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9b32a49eaf6"
down_revision: str | None = "e7a1c3f9b2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index(batch_op.f("ix_users_expires_at"), ["expires_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_expires_at"))
        batch_op.drop_column("expires_at")
