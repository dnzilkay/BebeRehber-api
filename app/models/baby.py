from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BabyGender(str, Enum):
    GIRL = "girl"
    BOY = "boy"
    UNSPECIFIED = "unspecified"


class Baby(Base):
    __tablename__ = "babies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[BabyGender] = mapped_column(
        SAEnum(
            BabyGender,
            name="baby_gender",
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=BabyGender.UNSPECIFIED,
        nullable=False,
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # passive_deletes=True → user silindiğinde ORM owner_id'yi NULL'a çekmek
    # yerine DB seviyesindeki ON DELETE CASCADE'i çalıştırsın
    owner = relationship(
        "User",
        backref=backref("babies", passive_deletes=True),
        passive_deletes=True,
    )
