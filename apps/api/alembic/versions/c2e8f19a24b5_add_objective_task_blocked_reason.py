"""Add blocked_reason to objective tasks for Task 8.1.

Revision ID: c2e8f19a24b5
Revises: b1d7e68f18a3
Create Date: 2026-08-26 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c2e8f19a24b5"
down_revision: str | None = "b1d7e68f18a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("objective_tasks", sa.Column("blocked_reason", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("objective_tasks", "blocked_reason")
