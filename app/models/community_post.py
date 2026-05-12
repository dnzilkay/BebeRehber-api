from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CommunityCategory(str, Enum):
    SLEEP = "sleep"
    FEEDING = "feeding"
    DEVELOPMENT = "development"
    HEALTH = "health"
    GENERAL = "general"


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[CommunityCategory] = mapped_column(
        SAEnum(
            CommunityCategory,
            name="community_category",
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=CommunityCategory.GENERAL,
        index=True,
    )
    is_expert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    comments = relationship(
        "CommunityComment",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="CommunityComment.created_at",
    )
