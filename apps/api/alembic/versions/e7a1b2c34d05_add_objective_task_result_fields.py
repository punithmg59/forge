"""Add founder result capture fields to objective_tasks.

Revision ID: e7a1b2c34d05
Revises: d4e8a1c92f03
Create Date: 2026-08-24 22:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e7a1b2c34d05"
down_revision: str | None = "d4e8a1c92f03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("objective_tasks", sa.Column("result_summary", sa.String(), nullable=True))
    op.add_column(
        "objective_tasks",
        sa.Column("result_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("objective_tasks", sa.Column("result_notes", sa.String(), nullable=True))
    op.add_column("objective_tasks", sa.Column("completed_by", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_objective_tasks_completed_by_users",
        "objective_tasks",
        "users",
        ["completed_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_objective_tasks_completed_by_users",
        "objective_tasks",
        type_="foreignkey",
    )
    op.drop_column("objective_tasks", "completed_by")
    op.drop_column("objective_tasks", "result_notes")
    op.drop_column("objective_tasks", "result_metrics")
    op.drop_column("objective_tasks", "result_summary")
