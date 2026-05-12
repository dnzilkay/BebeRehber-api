"""journal: albums + journal_entries + media_assets

Revision ID: 0006_journal
Revises: 0005_milestones
Create Date: 2026-05-12 09:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0006_journal"
down_revision: Union[str, None] = "0005_milestones"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "albums",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("baby_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("cover_object_key", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["baby_id"], ["babies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_albums_id"), "albums", ["id"], unique=False)
    op.create_index(op.f("ix_albums_baby_id"), "albums", ["baby_id"], unique=False)

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("baby_id", sa.Integer(), nullable=False),
        sa.Column("album_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["baby_id"], ["babies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_journal_entries_id"), "journal_entries", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_journal_entries_baby_id"),
        "journal_entries",
        ["baby_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_journal_entries_album_id"),
        "journal_entries",
        ["album_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_journal_entries_occurred_on"),
        "journal_entries",
        ["occurred_on"],
        unique=False,
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "image",
                "video",
                name="media_kind",
                native_enum=False,
                length=8,
            ),
            nullable=False,
        ),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["journal_entries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_media_assets_id"), "media_assets", ["id"], unique=False)
    op.create_index(
        op.f("ix_media_assets_entry_id"), "media_assets", ["entry_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_media_assets_entry_id"), table_name="media_assets")
    op.drop_index(op.f("ix_media_assets_id"), table_name="media_assets")
    op.drop_table("media_assets")

    op.drop_index(op.f("ix_journal_entries_occurred_on"), table_name="journal_entries")
    op.drop_index(op.f("ix_journal_entries_album_id"), table_name="journal_entries")
    op.drop_index(op.f("ix_journal_entries_baby_id"), table_name="journal_entries")
    op.drop_index(op.f("ix_journal_entries_id"), table_name="journal_entries")
    op.drop_table("journal_entries")

    op.drop_index(op.f("ix_albums_baby_id"), table_name="albums")
    op.drop_index(op.f("ix_albums_id"), table_name="albums")
    op.drop_table("albums")
