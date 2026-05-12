"""baby_members + baby_invites tabloları + mevcut owner backfill.

Modül 6: aile paylaşımı (Premium).

Revision ID: 0008_baby_sharing
Revises: 0007_enum_lowercase
Create Date: 2026-05-12 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0008_baby_sharing"
down_revision: Union[str, None] = "0007_enum_lowercase"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "baby_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("baby_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "owner",
                "co_parent",
                name="baby_member_role",
                native_enum=False,
                length=16,
            ),
            nullable=False,
            server_default="co_parent",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["baby_id"], ["babies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "baby_id", "user_id", name="uq_baby_member_baby_user"
        ),
    )
    op.create_index(op.f("ix_baby_members_id"), "baby_members", ["id"])
    op.create_index(op.f("ix_baby_members_baby_id"), "baby_members", ["baby_id"])
    op.create_index(op.f("ix_baby_members_user_id"), "baby_members", ["user_id"])

    op.create_table(
        "baby_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("baby_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["baby_id"], ["babies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["used_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_baby_invite_token"),
    )
    op.create_index(op.f("ix_baby_invites_id"), "baby_invites", ["id"])
    op.create_index(op.f("ix_baby_invites_baby_id"), "baby_invites", ["baby_id"])
    op.create_index(op.f("ix_baby_invites_token"), "baby_invites", ["token"])

    # Backfill: her mevcut bebek için owner kaydı oluştur
    op.execute(
        "INSERT INTO baby_members (baby_id, user_id, role, created_at) "
        "SELECT id, owner_id, 'owner', created_at FROM babies"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_baby_invites_token"), table_name="baby_invites")
    op.drop_index(op.f("ix_baby_invites_baby_id"), table_name="baby_invites")
    op.drop_index(op.f("ix_baby_invites_id"), table_name="baby_invites")
    op.drop_table("baby_invites")

    op.drop_index(op.f("ix_baby_members_user_id"), table_name="baby_members")
    op.drop_index(op.f("ix_baby_members_baby_id"), table_name="baby_members")
    op.drop_index(op.f("ix_baby_members_id"), table_name="baby_members")
    op.drop_table("baby_members")
