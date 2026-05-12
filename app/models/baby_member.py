from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class BabyMemberRole(str, Enum):
    OWNER = "owner"
    CO_PARENT = "co_parent"


class BabyMember(Base):
    """Bir bebeğe erişim hakkı olan kullanıcı kaydı.

    - Baby oluşturulurken 'owner' rolüyle bir kayıt eklenir.
    - Premium owner, BabyInvite token ile başka kullanıcıyı 'co_parent'
      olarak ekleyebilir.
    """

    __tablename__ = "baby_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    baby_id: Mapped[int] = mapped_column(
        ForeignKey("babies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[BabyMemberRole] = mapped_column(
        SAEnum(
            BabyMemberRole,
            name="baby_member_role",
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=BabyMemberRole.CO_PARENT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("baby_id", "user_id", name="uq_baby_member_baby_user"),
    )
