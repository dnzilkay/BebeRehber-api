from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class BabyMemberRole(str, Enum):
    """Sistem rolü — erişim seviyesi (owner / co_parent).

    Bu kullanıcının bebek-bağlamlı yetkilerini belirler. Aile ilişkisinden
    bağımsız: owner kendisi anne / baba / bakıcı her şey olabilir.
    """

    OWNER = "owner"
    CO_PARENT = "co_parent"


class BabyRelationship(str, Enum):
    """Bebekle aile ilişkisi (UI rolü) — sistem rolünden bağımsız.

    Birden fazla kişi 'anne' veya 'baba' olabilir (örn ikiz anne, üvey baba).
    Demo'da kişi kim olduğunu belirtmek için kullanılır; otomatik bir yetki
    devri yapmaz.
    """

    MOTHER = "mother"
    FATHER = "father"
    CAREGIVER = "caregiver"  # Bakıcı
    GRANDMOTHER = "grandmother"  # Büyükanne / anneanne
    GRANDFATHER = "grandfather"  # Büyükbaba / dede
    OTHER = "other"  # Serbest metin için


class BabyMember(Base):
    """Bir bebeğe erişim hakkı olan kullanıcı kaydı.

    - Baby oluşturulurken 'owner' rolüyle bir kayıt eklenir.
    - Premium owner, BabyInvite token ile başka kullanıcıyı 'co_parent'
      olarak ekleyebilir.
    - Üye kendi `relationship` ve `relationship_label`'ını seçebilir
      ("anne" / "baba" / "bakıcı" / vb. + isteğe bağlı serbest metin).
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
    # Aile ilişkisi — başlangıçta NULL, kullanıcı profilinden seçer
    relationship: Mapped[BabyRelationship | None] = mapped_column(
        SAEnum(
            BabyRelationship,
            name="baby_relationship",
            native_enum=False,
            length=24,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
    )
    # Sadece relationship=other ise dolar; "Vaftiz annesi" gibi.
    relationship_label: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("baby_id", "user_id", name="uq_baby_member_baby_user"),
    )
