"""care_logs table

Revision ID: 0003_care_logs
Revises: 0002_babies
Create Date: 2026-05-04 15:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0003_care_logs"
down_revision: Union[str, None] = "0002_babies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "care_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("baby_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "sleep",
                "feeding",
                "diaper",
                name="care_kind",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount_ml", sa.Integer(), nullable=True),
        sa.Column(
            "diaper_type",
            sa.Enum(
                "pee",
                "poop",
                "both",
                name="diaper_type",
                native_enum=False,
                length=8,
            ),
            nullable=True,
        ),
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
    op.create_index(op.f("ix_care_logs_id"), "care_logs", ["id"], unique=False)
    op.create_index(
        op.f("ix_care_logs_baby_id"), "care_logs", ["baby_id"], unique=False
    )
    op.create_index(op.f("ix_care_logs_kind"), "care_logs", ["kind"], unique=False)
    op.create_index(
        op.f("ix_care_logs_started_at"),
        "care_logs",
        ["started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_care_logs_started_at"), table_name="care_logs")
    op.drop_index(op.f("ix_care_logs_kind"), table_name="care_logs")
    op.drop_index(op.f("ix_care_logs_baby_id"), table_name="care_logs")
    op.drop_index(op.f("ix_care_logs_id"), table_name="care_logs")
    op.drop_table("care_logs")
