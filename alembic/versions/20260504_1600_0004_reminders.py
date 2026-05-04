"""reminders table

Revision ID: 0004_reminders
Revises: 0003_care_logs
Create Date: 2026-05-04 16:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0004_reminders"
down_revision: Union[str, None] = "0003_care_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("baby_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "vaccine",
                "appointment",
                "general",
                name="reminder_kind",
                native_enum=False,
                length=16,
            ),
            nullable=False,
            server_default="general",
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["baby_id"], ["babies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reminders_id"), "reminders", ["id"], unique=False)
    op.create_index(
        op.f("ix_reminders_baby_id"), "reminders", ["baby_id"], unique=False
    )
    op.create_index(op.f("ix_reminders_kind"), "reminders", ["kind"], unique=False)
    op.create_index(op.f("ix_reminders_due_at"), "reminders", ["due_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reminders_due_at"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_kind"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_baby_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_id"), table_name="reminders")
    op.drop_table("reminders")
