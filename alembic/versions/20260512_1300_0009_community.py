"""community_posts + community_comments tabloları.

Modül 7: Topluluk Portalı (Premium).

Revision ID: 0009_community
Revises: 0008_baby_sharing
Create Date: 2026-05-12 13:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0009_community"
down_revision: Union[str, None] = "0008_baby_sharing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "sleep",
                "feeding",
                "development",
                "health",
                "general",
                name="community_category",
                native_enum=False,
                length=16,
            ),
            nullable=False,
            server_default="general",
        ),
        sa.Column(
            "is_expert",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_community_posts_id"), "community_posts", ["id"])
    op.create_index(
        op.f("ix_community_posts_author_id"),
        "community_posts",
        ["author_id"],
    )
    op.create_index(
        op.f("ix_community_posts_category"),
        "community_posts",
        ["category"],
    )

    op.create_table(
        "community_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["community_posts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_community_comments_id"), "community_comments", ["id"]
    )
    op.create_index(
        op.f("ix_community_comments_post_id"),
        "community_comments",
        ["post_id"],
    )
    op.create_index(
        op.f("ix_community_comments_author_id"),
        "community_comments",
        ["author_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_community_comments_author_id"), table_name="community_comments"
    )
    op.drop_index(
        op.f("ix_community_comments_post_id"), table_name="community_comments"
    )
    op.drop_index(op.f("ix_community_comments_id"), table_name="community_comments")
    op.drop_table("community_comments")

    op.drop_index(op.f("ix_community_posts_category"), table_name="community_posts")
    op.drop_index(op.f("ix_community_posts_author_id"), table_name="community_posts")
    op.drop_index(op.f("ix_community_posts_id"), table_name="community_posts")
    op.drop_table("community_posts")
