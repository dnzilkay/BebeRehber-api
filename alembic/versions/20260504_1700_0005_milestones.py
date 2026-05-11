"""milestones table

Revision ID: 0005_milestones
Revises: 0004_reminders
Create Date: 2026-05-04 17:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0005_milestones"
down_revision: Union[str, None] = "0004_reminders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "milestones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("baby_id", sa.Integer(), nullable=False),
        sa.Column("preset_id", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "motor",
                "cognitive",
                "social",
                "language",
                "physical",
                "other",
                name="milestone_category",
                native_enum=False,
                length=16,
            ),
            nullable=False,
            server_default="other",
        ),
        sa.Column("reached_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["baby_id"], ["babies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_milestones_id"), "milestones", ["id"], unique=False)
    op.create_index(
        op.f("ix_milestones_baby_id"), "milestones", ["baby_id"], unique=False
    )
    op.create_index(
        op.f("ix_milestones_preset_id"), "milestones", ["preset_id"], unique=False
    )
    op.create_index(
        op.f("ix_milestones_category"), "milestones", ["category"], unique=False
    )
    op.create_index(
        op.f("ix_milestones_reached_on"), "milestones", ["reached_on"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_milestones_reached_on"), table_name="milestones")
    op.drop_index(op.f("ix_milestones_category"), table_name="milestones")
    op.drop_index(op.f("ix_milestones_preset_id"), table_name="milestones")
    op.drop_index(op.f("ix_milestones_baby_id"), table_name="milestones")
    op.drop_index(op.f("ix_milestones_id"), table_name="milestones")
    op.drop_table("milestones")
