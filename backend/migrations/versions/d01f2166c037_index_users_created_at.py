"""index users created at

UM-US-03 T-01 / plan.md A3: the list-users endpoint sorts newest-first on
`users.created_at` (spec BR-04, FR-08), and constitution PF-02 requires an
index on any column carrying an `ORDER BY`. No column change — index only.

batch_alter_table because SQLite cannot ALTER most things in place
(render_as_batch=True in migrations/env.py), matching the pattern the initial
revision already uses for `ix_users_email`.

Revision ID: d01f2166c037
Revises: c9d6ddbb50f4
Create Date: 2026-08-11 06:47:10.554509
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d01f2166c037"
down_revision: str | None = "c9d6ddbb50f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_users_created_at"), ["created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_created_at"))
