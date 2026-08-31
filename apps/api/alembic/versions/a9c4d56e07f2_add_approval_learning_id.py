"""Add learning provenance to approvals for Task 7.4.

Revision ID: a9c4d56e07f2
Revises: f8b3c45d06e1
Create Date: 2026-08-24 23:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9c4d56e07f2"
down_revision: str | None = "f8b3c45d06e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("approvals", sa.Column("learning_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_approvals_learning_id_learnings",
        "approvals",
        "learnings",
        ["learning_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_approvals_learning_id", "approvals", ["learning_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_approvals_learning_id", table_name="approvals")
    op.drop_constraint("fk_approvals_learning_id_learnings", "approvals", type_="foreignkey")
    op.drop_column("approvals", "learning_id")
