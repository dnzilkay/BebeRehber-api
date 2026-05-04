from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class CareKind(str, Enum):
    SLEEP = "sleep"
    FEEDING = "feeding"
    DIAPER = "diaper"


class DiaperType(str, Enum):
    PEE = "pee"
    POOP = "poop"
    BOTH = "both"


class CareLog(Base):
    __tablename__ = "care_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    baby_id: Mapped[int] = mapped_column(
        ForeignKey("babies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[CareKind] = mapped_column(
        SAEnum(CareKind, name="care_kind", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    amount_ml: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diaper_type: Mapped[DiaperType | None] = mapped_column(
        SAEnum(DiaperType, name="diaper_type", native_enum=False, length=8),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
