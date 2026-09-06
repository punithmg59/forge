"""Add plan fingerprint and expiration to approvals for Task 9.8.4.

Revision ID: add_execution_approval_fingerprint
Revises: c2e8f19a24b5
Create Date: 2026-08-31 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_execution_approval_fingerprint"
down_revision: str | None = "c2e8f19a24b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("approvals", sa.Column("plan_fingerprint", sa.String(length=64), nullable=True))
    op.add_column("approvals", sa.Column("expires_at", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("approvals", "expires_at")
    op.drop_column("approvals", "plan_fingerprint")
