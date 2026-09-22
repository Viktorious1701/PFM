"""create categories table

CM-US-01 T-02 (spec BR-01; plan.md T-01, T-02). One row per category, owned by
exactly one user (SRS §1.5 "User defines Category"; constitution SEC-08).

Index design (plan.md, constitution PF-02, SEC-08):

  ix_categories_user_id   not unique — every future query on this table
                          filters by owner, so the FK is indexed now, ahead
                          of CM-US-02's need for it.

No `icon` column (plan.md A4) — CM-US-01's own AC set never mentions `icon`;
adding it here would pre-empt CM-US-04, the story whose goal actually names
icon-editing. `type` is a real `Enum` column (plan.md A2), not free text like
`wallets.type`/`wallets.currency`.

Revision ID: 81bfb85427ed
Revises: 022fc9649eb5
Create Date: 2026-09-22 02:10:38.202175
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "81bfb85427ed"
down_revision: str | None = "022fc9649eb5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "type",
            sa.Enum("INCOME", "EXPENSE", name="categorytype", native_enum=False, length=10),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # batch_alter_table because SQLite cannot ALTER most things in place
    # (render_as_batch=True in migrations/env.py).
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_categories_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_categories_user_id"))

    op.drop_table("categories")
