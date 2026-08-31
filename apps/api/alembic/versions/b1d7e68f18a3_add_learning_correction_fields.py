"""Add correction audit fields to learnings for Task 7.5.

Revision ID: b1d7e68f18a3
Revises: a9c4d56e07f2
Create Date: 2026-08-24 23:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b1d7e68f18a3"
down_revision: str | None = "a9c4d56e07f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("learnings", sa.Column("corrected_by", sa.UUID(), nullable=True))
    op.add_column(
        "learnings",
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("learnings", sa.Column("correction_reason", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_learnings_corrected_by_users",
        "learnings",
        "users",
        ["corrected_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_learnings_corrected_by_users", "learnings", type_="foreignkey")
    op.drop_column("learnings", "correction_reason")
    op.drop_column("learnings", "corrected_at")
    op.drop_column("learnings", "corrected_by")
