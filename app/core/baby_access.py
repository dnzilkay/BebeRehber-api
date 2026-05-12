"""Bebek erişim kontrolü — owner veya co_parent her ikisi de tüm bebek
endpoint'lerini kullanabilir. Modül 6: aile paylaşımı."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.baby import Baby
from app.models.baby_member import BabyMember, BabyMemberRole


def is_baby_member(db: Session, user_id: int, baby_id: int) -> bool:
    """Kullanıcı bebeğin owner veya co_parent üyesi mi?"""
    return (
        db.scalar(
            select(BabyMember.id).where(
                BabyMember.baby_id == baby_id, BabyMember.user_id == user_id
            )
        )
        is not None
    )


def is_baby_owner(db: Session, user_id: int, baby_id: int) -> bool:
    row = db.scalar(
        select(BabyMember.role).where(
            BabyMember.baby_id == baby_id, BabyMember.user_id == user_id
        )
    )
    return row == BabyMemberRole.OWNER


def ensure_baby_access(db: Session, user_id: int, baby_id: int) -> Baby:
    """Bebek vardır + kullanıcı üyedir; aksi takdirde 404 fırlat.

    Owner olmayan üyelere de tam erişim verir (proje.md aile paylaşımı:
    "bakım verileri eş zamanlı görüntülenir / paylaşılır"). Sadece
    member yönetimi (invite/remove) owner'a özeldir, o ayrı kontrol
    edilir.
    """
    baby = db.get(Baby, baby_id)
    if baby is None or not is_baby_member(db, user_id, baby_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bebek bulunamadı.",
        )
    return baby


def ensure_baby_owner(db: Session, user_id: int, baby_id: int) -> Baby:
    """Owner-only işlemler (invite oluştur, üye çıkar) için katı kontrol."""
    baby = db.get(Baby, baby_id)
    if baby is None or not is_baby_member(db, user_id, baby_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bebek bulunamadı.",
        )
    if not is_baby_owner(db, user_id, baby_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için bebeğin sahibi olmalısın.",
        )
    return baby
