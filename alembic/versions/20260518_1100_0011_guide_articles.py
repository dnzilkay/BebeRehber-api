"""guide_articles tablosu — herkese açık rehber yazıları (admin yazar).

BACKLOG #2: Hamilelik ve bebek gelişimi bilgilendirici içerikler.

Revision ID: 0011_guide_articles
Revises: 0010_social
Create Date: 2026-05-18 11:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0011_guide_articles"
down_revision: Union[str, None] = "0010_social"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guide_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "pregnancy",
                "newborn",
                "infant",
                "older_infant",
                "toddler",
                name="guide_category",
                native_enum=False,
                length=24,
            ),
            nullable=False,
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
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_guide_articles_id"), "guide_articles", ["id"])
    op.create_index(
        op.f("ix_guide_articles_slug"), "guide_articles", ["slug"], unique=True
    )
    op.create_index(op.f("ix_guide_articles_category"), "guide_articles", ["category"])
    op.create_index(
        op.f("ix_guide_articles_author_id"), "guide_articles", ["author_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_guide_articles_author_id"), table_name="guide_articles")
    op.drop_index(op.f("ix_guide_articles_category"), table_name="guide_articles")
    op.drop_index(op.f("ix_guide_articles_slug"), table_name="guide_articles")
    op.drop_index(op.f("ix_guide_articles_id"), table_name="guide_articles")
    op.drop_table("guide_articles")
