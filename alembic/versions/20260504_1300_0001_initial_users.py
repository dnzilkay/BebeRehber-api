"""initial users table

Revision ID: 0001_initial_users
Revises:
Create Date: 2026-05-04 13:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0001_initial_users"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_plan = sa.Enum("free", "premium", name="user_plan")
    user_role = sa.Enum("user", "admin", name="user_role")
    user_plan.create(op.get_bind(), checkfirst=True)
    user_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "plan",
            sa.Enum("free", "premium", name="user_plan", create_type=False),
            nullable=False,
            server_default="free",
        ),
        sa.Column(
            "role",
            sa.Enum("user", "admin", name="user_role", create_type=False),
            nullable=False,
            server_default="user",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_plan").drop(op.get_bind(), checkfirst=True)
