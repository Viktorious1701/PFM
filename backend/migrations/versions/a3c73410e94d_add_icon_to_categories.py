"""add icon to categories

CM-US-04 T-01 (plan.md A5). The first schema change to `categories` since its
own creation (81bfb85427ed) -- CM-US-01 A4 deferred this exact column to
"CM-US-04's own decision to make, since CM-US-04 ... is the story whose goal
actually names icon-editing."

Nullable, no default: every category CM-US-01/02 already created has no value
for it, and no AC requires a default other than absent. Length 50, not
`name`'s own 100 -- an icon is expected to be a short identifier or slug, not
a label-length piece of text (plan.md A11).

batch_alter_table because SQLite cannot ALTER most things in place
(render_as_batch=True in migrations/env.py), matching every other column/index
change in this codebase.

Revision ID: a3c73410e94d
Revises: f3a9c1d4e8b2
Create Date: 2026-10-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3c73410e94d"
down_revision: str | None = "f3a9c1d4e8b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("icon", sa.String(length=50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.drop_column("icon")
