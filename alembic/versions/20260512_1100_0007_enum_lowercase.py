"""Enum kolonlarındaki uppercase değerleri lowercase'e dönüştür.

Tarihçe: önceki SAEnum tanımları values_callable kullanmıyordu, bu yüzden
SQLAlchemy diske enum.name (FREE/PREMIUM/...) uppercase yazıyordu. Migration
constraint'leri ise lowercase ('free', 'premium', ...) bekliyor. Bu mismatch
manual SQL update'lerinde 500 LookupError'a sebep oluyordu.

Bu migration:
1. Mevcut uppercase satırları lowercase'e çevirir.
2. Modeller artık values_callable=lambda e: [m.value for m in e] ile
   yazıldığı için yeni veriler doğrudan lowercase yazılacak.

Revision ID: 0007_enum_lowercase
Revises: 0006_journal
Create Date: 2026-05-12 11:00:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0007_enum_lowercase"
down_revision: Union[str, None] = "0006_journal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column) → her zaman LOWER() güvenli
COLUMNS: list[tuple[str, str]] = [
    ("users", "plan"),
    ("users", "role"),
    ("babies", "gender"),
    ("care_logs", "kind"),
    ("care_logs", "diaper_type"),
    ("reminders", "kind"),
    ("milestones", "category"),
    ("media_assets", "kind"),
]


def upgrade() -> None:
    for table, column in COLUMNS:
        op.execute(
            f"UPDATE {table} SET {column} = LOWER({column}) "
            f"WHERE {column} IS NOT NULL AND {column} <> LOWER({column})"
        )


def downgrade() -> None:
    for table, column in COLUMNS:
        op.execute(
            f"UPDATE {table} SET {column} = UPPER({column}) "
            f"WHERE {column} IS NOT NULL AND {column} <> UPPER({column})"
        )
