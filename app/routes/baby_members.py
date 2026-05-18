"""Aile paylaşımı — bebek üyeleri (owner + co-parent) ve davet token'ları.

Owner Premium kullanıcı davet üretir, paylaşır. Token'ı kabul eden user
bebek üyeliğine eklenir (Free olsa bile co-parent olabilir).
"""

import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.baby_access import ensure_baby_access, ensure_baby_owner
from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.limits import is_premium
from app.models.baby_invite import BabyInvite
from app.models.baby_member import BabyMember, BabyMemberRole
from app.models.user import User
from app.schemas.baby_invite import BabyInviteAcceptOut, BabyInviteOut
from app.schemas.baby_member import BabyMemberOut


INVITE_TTL_DAYS = 7

# Human-readable 10 char uppercase alphanumeric — hem URL'de hem manuel
# girilebilir (yanlışlık olmasın diye 0/O ve 1/I/L gibi karışan harfler
# kaldırıldı). 32^10 ≈ 1.1e15 → tek kullanımlık + 7 gün TTL ile yeterince güvenli.
_INVITE_CODE_ALPHABET = "".join(
    c for c in string.ascii_uppercase + string.digits if c not in "O0I1L"
)


def _gen_invite_code() -> str:
    return "".join(secrets.choice(_INVITE_CODE_ALPHABET) for _ in range(10))


# ---------------------------- Members listing ----------------------------

baby_router = APIRouter(prefix="/babies/{baby_id}", tags=["baby-sharing"])


def _member_out(member: BabyMember, user: User) -> BabyMemberOut:
    return BabyMemberOut(
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        role=member.role,
        created_at=member.created_at,
    )


@baby_router.get(
    "/members",
    response_model=list[BabyMemberOut],
    summary="Bu bebeğe erişimi olan üyeler",
)
def list_members(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> list[BabyMemberOut]:
    ensure_baby_access(db, current_user.id, baby_id)

    rows = db.execute(
        select(BabyMember, User)
        .join(User, BabyMember.user_id == User.id)
        .where(BabyMember.baby_id == baby_id)
        .order_by(BabyMember.created_at.asc())
    ).all()
    return [_member_out(m, u) for m, u in rows]


@baby_router.delete(
    "/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Co-parent üyeyi çıkar (owner only, owner kendi kendini çıkaramaz)",
)
def remove_member(
    baby_id: int,
    user_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    ensure_baby_owner(db, current_user.id, baby_id)

    member = db.scalar(
        select(BabyMember).where(
            BabyMember.baby_id == baby_id, BabyMember.user_id == user_id
        )
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Üye bulunamadı."
        )
    if member.role == BabyMemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner çıkarılamaz. Bebek profilini silmek için DELETE /babies/{id} kullan.",
        )
    db.delete(member)
    db.commit()


# ---------------------------- Invites -----------------------------------


@baby_router.post(
    "/invites",
    response_model=BabyInviteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Premium owner: co-parent davet linki üret",
)
def create_invite(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> BabyInviteOut:
    ensure_baby_owner(db, current_user.id, baby_id)

    if not is_premium(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Aile paylaşımı Premium pakette yer alır. "
                "Bebek profilini başka ebeveynle paylaşmak için Premium'a geç."
            ),
        )

    # Çakışma olasılığı çok düşük ama gen tekrarı koru
    token = _gen_invite_code()
    while db.scalar(select(BabyInvite).where(BabyInvite.token == token)):
        token = _gen_invite_code()
    expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_TTL_DAYS)

    invite = BabyInvite(
        baby_id=baby_id,
        created_by_user_id=current_user.id,
        token=token,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    url = f"{settings.FRONTEND_URL.rstrip('/')}/invite/{token}"
    return BabyInviteOut(
        token=token,
        url=url,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


# ---------------------------- Invite accept -----------------------------

invites_router = APIRouter(prefix="/invites", tags=["baby-sharing"])


@invites_router.post(
    "/accept/{token}",
    response_model=BabyInviteAcceptOut,
    summary="Davet token'ını kabul et — co-parent olarak bebeğe katıl",
)
def accept_invite(
    token: str,
    current_user: CurrentUser,
    db: DbSession,
) -> BabyInviteAcceptOut:
    # Manuel kod girişinde küçük harf / aralık olabilir — normalize et
    normalized = token.strip().upper().replace(" ", "").replace("-", "")
    invite = db.scalar(select(BabyInvite).where(BabyInvite.token == normalized))
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Davet bulunamadı."
        )
    if invite.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Bu davet daha önce kullanılmış.",
        )

    now = datetime.now(timezone.utc)
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Bu davetin süresi dolmuş.",
        )

    # Zaten üye mi?
    existing = db.scalar(
        select(BabyMember).where(
            BabyMember.baby_id == invite.baby_id,
            BabyMember.user_id == current_user.id,
        )
    )
    if existing is None:
        db.add(
            BabyMember(
                baby_id=invite.baby_id,
                user_id=current_user.id,
                role=BabyMemberRole.CO_PARENT,
            )
        )

    invite.used_at = now
    invite.used_by_user_id = current_user.id
    db.commit()

    # Bebek ismi
    from app.models.baby import Baby

    baby = db.get(Baby, invite.baby_id)
    return BabyInviteAcceptOut(
        baby_id=invite.baby_id,
        baby_name=baby.name if baby else "",
    )
