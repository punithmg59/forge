"""Align memory embeddings with NVIDIA nv-embedqa-e5-v5 (1024 dims).

Revision ID: d4e8a1c92f03
Revises: c8f5d2b13e01
Create Date: 2026-08-23 14:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "d4e8a1c92f03"
down_revision: Union[str, None] = "c8f5d2b13e01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE memories SET embedding = NULL WHERE embedding IS NOT NULL")
    op.execute("ALTER TABLE memories ALTER COLUMN embedding TYPE vector(1024)")


def downgrade() -> None:
    op.execute("UPDATE memories SET embedding = NULL WHERE embedding IS NOT NULL")
    op.execute("ALTER TABLE memories ALTER COLUMN embedding TYPE vector(1536)")
