"""Add evidence provenance to learnings for Task 7.3 proposals.

Revision ID: f8b3c45d06e1
Revises: e7a1b2c34d05
Create Date: 2026-08-24 23:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f8b3c45d06e1"
down_revision: str | None = "e7a1b2c34d05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("learnings", sa.Column("evidence_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_learnings_evidence_id_evidence",
        "learnings",
        "evidence",
        ["evidence_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_learnings_evidence_id", "learnings", ["evidence_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_learnings_evidence_id", table_name="learnings")
    op.drop_constraint("fk_learnings_evidence_id_evidence", "learnings", type_="foreignkey")
    op.drop_column("learnings", "evidence_id")
