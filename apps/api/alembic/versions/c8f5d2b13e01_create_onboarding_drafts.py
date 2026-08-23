"""create onboarding_drafts table

Revision ID: c8f5d2b13e01
Revises: b7e4c1a90d12
Create Date: 2026-08-23 12:55:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c8f5d2b13e01"
down_revision: Union[str, None] = "b7e4c1a90d12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "onboarding_drafts",
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_onboarding_drafts_company_id"),
    )
    op.create_index(
        "ix_onboarding_drafts_company_id", "onboarding_drafts", ["company_id"], unique=False
    )
    op.create_index("ix_onboarding_drafts_status", "onboarding_drafts", ["status"], unique=False)
    op.create_index(
        "ix_onboarding_drafts_created_by_user_id",
        "onboarding_drafts",
        ["created_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_onboarding_drafts_created_by_user_id", table_name="onboarding_drafts")
    op.drop_index("ix_onboarding_drafts_status", table_name="onboarding_drafts")
    op.drop_index("ix_onboarding_drafts_company_id", table_name="onboarding_drafts")
    op.drop_table("onboarding_drafts")
