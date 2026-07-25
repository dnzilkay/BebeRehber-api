"""Audit helper — `created_by_user_id` + bebek bağlamından `ActorOut` üretir.

Endpoint'lerde tek tek lookup yerine, çoğu yer bir bebek + bir actor için
soruyor. Batch (çoklu user) için ileride optimize edilebilir; demo'da
N+1 yeterli performans veriyor.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.baby_member import BabyMember
from app.models.user import User
from app.schemas.audit import ActorOut


def actor_for(db: Session, baby_id: int, user_id: int | None) -> ActorOut | None:
    """Kullanıcı + bebek-bağlamlı ilişki bilgisi ile ActorOut döndür.

    `user_id` None ise (kayıt eski / kaydedenin hesabı silinmiş) None döner.
    """
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None:
        return None
    member = db.scalar(
        select(BabyMember).where(
            BabyMember.baby_id == baby_id,
            BabyMember.user_id == user_id,
        )
    )
    return ActorOut(
        id=user.id,
        name=user.name,
        relationship=member.relationship if member else None,
        relationship_label=member.relationship_label if member else None,
    )
