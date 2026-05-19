from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class MilestoneCategory(str, Enum):
    MOTOR = "motor"
    COGNITIVE = "cognitive"
    SOCIAL = "social"
    LANGUAGE = "language"
    PHYSICAL = "physical"
    OTHER = "other"


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    baby_id: Mapped[int] = mapped_column(
        ForeignKey("babies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Önceden tanımlı milestone'ların stabil ID'si (örn. "first_smile").
    # Serbest metin notları için None.
    preset_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[MilestoneCategory] = mapped_column(
        SAEnum(
            MilestoneCategory,
            name="milestone_category",
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=MilestoneCategory.OTHER,
        nullable=False,
        index=True,
    )
    reached_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
