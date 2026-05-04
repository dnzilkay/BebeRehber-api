"""babies table

Revision ID: 0002_babies
Revises: 0001_initial_users
Create Date: 2026-05-04 14:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0002_babies"
down_revision: Union[str, None] = "0001_initial_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "babies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column(
            "gender",
            sa.Enum(
                "girl",
                "boy",
                "unspecified",
                name="baby_gender",
                native_enum=False,
                length=16,
            ),
            nullable=False,
            server_default="unspecified",
        ),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_babies_id"), "babies", ["id"], unique=False)
    op.create_index(op.f("ix_babies_owner_id"), "babies", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_babies_owner_id"), table_name="babies")
    op.drop_index(op.f("ix_babies_id"), table_name="babies")
    op.drop_table("babies")
