"""social_posts tablosu (sosyal medya içerik takvimi).

Modül 9: Sosyal Medya Yönetimi (Admin).

Revision ID: 0010_social
Revises: 0009_community
Create Date: 2026-05-12 15:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0010_social"
down_revision: Union[str, None] = "0009_community"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "social_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column(
            "platform",
            sa.Enum(
                "instagram",
                "tiktok",
                "x",
                "facebook",
                name="social_platform",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "scheduled",
                "published",
                name="social_post_status",
                native_enum=False,
                length=16,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reach", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_social_posts_id"), "social_posts", ["id"])
    op.create_index(op.f("ix_social_posts_author_id"), "social_posts", ["author_id"])
    op.create_index(op.f("ix_social_posts_platform"), "social_posts", ["platform"])
    op.create_index(op.f("ix_social_posts_status"), "social_posts", ["status"])
    op.create_index(
        op.f("ix_social_posts_scheduled_for"), "social_posts", ["scheduled_for"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_social_posts_scheduled_for"), table_name="social_posts")
    op.drop_index(op.f("ix_social_posts_status"), table_name="social_posts")
    op.drop_index(op.f("ix_social_posts_platform"), table_name="social_posts")
    op.drop_index(op.f("ix_social_posts_author_id"), table_name="social_posts")
    op.drop_index(op.f("ix_social_posts_id"), table_name="social_posts")
    op.drop_table("social_posts")
