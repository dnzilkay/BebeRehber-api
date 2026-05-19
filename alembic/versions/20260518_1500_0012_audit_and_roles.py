"""Aile audit: created_by_user_id + BabyMember.relationship/label.

Veliler bebek profilinde kim ne ekledi görsün ve aile içindeki rolünü
("anne" / "baba" / "bakıcı" / "büyükanne" / "büyükbaba" / "diğer (serbest)")
belirlesin.

Revision ID: 0012_audit_and_roles
Revises: 0011_guide_articles
Create Date: 2026-05-18 15:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "0012_audit_and_roles"
down_revision: Union[str, None] = "0011_guide_articles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_AUDIT_TABLES = [
    "care_logs",
    "milestones",
    "reminders",
    "journal_entries",
    "media_assets",
    "albums",
]


def upgrade() -> None:
    # 1) Her veri tablosuna nullable created_by_user_id + index + FK (SET NULL)
    for table in _AUDIT_TABLES:
        op.add_column(
            table,
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            f"fk_{table}_created_by_user_id_users",
            table,
            "users",
            ["created_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            f"ix_{table}_created_by_user_id",
            table,
            ["created_by_user_id"],
        )

    # 2) baby_members'a relationship enum + relationship_label (text)
    op.add_column(
        "baby_members",
        sa.Column(
            "relationship",
            sa.Enum(
                "mother",
                "father",
                "caregiver",
                "grandmother",
                "grandfather",
                "other",
                name="baby_relationship",
                native_enum=False,
                length=24,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "baby_members",
        sa.Column("relationship_label", sa.String(length=60), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("baby_members", "relationship_label")
    op.drop_column("baby_members", "relationship")

    for table in _AUDIT_TABLES:
        op.drop_index(f"ix_{table}_created_by_user_id", table_name=table)
        op.drop_constraint(
            f"fk_{table}_created_by_user_id_users", table, type_="foreignkey"
        )
        op.drop_column(table, "created_by_user_id")
