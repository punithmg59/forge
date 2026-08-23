"""Initial Alembic foundation.

Revision ID: 0001_initial_foundation
Revises:
Create Date: 2026-08-22 20:55:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001_initial_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
