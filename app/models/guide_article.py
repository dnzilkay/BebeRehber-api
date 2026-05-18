from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class GuideCategory(str, Enum):
    PREGNANCY = "pregnancy"
    NEWBORN = "newborn"  # 0-3 ay
    INFANT = "infant"  # 3-6 ay
    OLDER_INFANT = "older_infant"  # 6-12 ay
    TODDLER = "toddler"  # 12+ ay


class GuideArticle(Base):
    """Free dahil herkese açık, admin tarafından yazılan rehber yazıları."""

    __tablename__ = "guide_articles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # URL-dostu, benzersiz handle
    slug: Mapped[str] = mapped_column(
        String(160), nullable=False, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[GuideCategory] = mapped_column(
        SAEnum(
            GuideCategory,
            name="guide_category",
            native_enum=False,
            length=24,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
