"""Admin paneli endpoint'leri — sadece admin role'üne sahip kullanıcılar.

Kapsam:
- Kullanıcı listesi (arama + sayfa)
- Kullanıcı düzenle (plan/role/active/name)
- Kullanıcı sil
- Platform istatistikleri (özet metrikler)

Not: Topluluk içeriği moderasyonu (post/comment sil) zaten /community
route'larında admin'e açık. Aile paylaşımı ve dijital günlük tarafı için
özel admin endpoint'i şu an yok — kullanıcı silindiğinde CASCADE ile
tüm içerikler otomatik temizlenir.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.core.deps import CurrentUser, DbSession
from app.models.baby import Baby
from app.models.community_comment import CommunityComment
from app.models.community_post import CommunityPost
from app.models.journal_entry import JournalEntry
from app.models.media_asset import MediaAsset
from app.models.user import User, UserRole
from app.schemas.admin import AdminStats, AdminUserOut, AdminUserUpdate


router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu sayfaya yalnızca yöneticiler erişebilir.",
        )


def _user_out(user: User, baby_count: int) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        plan=user.plan,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        baby_count=baby_count,
    )


# --------------------------- Users --------------------------------------


@router.get(
    "/users",
    response_model=list[AdminUserOut],
    summary="Kullanıcı listesi (arama + sayfa)",
)
def list_users(
    current_user: CurrentUser,
    db: DbSession,
    q: str | None = Query(default=None, max_length=120),
    plan: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AdminUserOut]:
    _require_admin(current_user)

    # Kullanıcı başına bebek sayısı (owner tablosundan)
    stmt = (
        select(User, func.count(Baby.id))
        .outerjoin(Baby, Baby.owner_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc(), User.id.desc())
    )
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(User.email).like(like),
                func.lower(User.name).like(like),
            )
        )
    if plan:
        stmt = stmt.where(User.plan == plan)
    stmt = stmt.limit(limit).offset(offset)

    rows = db.execute(stmt).all()
    return [_user_out(u, cnt or 0) for u, cnt in rows]


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserOut,
    summary="Kullanıcıyı güncelle (plan / role / aktiflik / isim)",
)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> AdminUserOut:
    _require_admin(current_user)

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı."
        )

    # Kendi adminliğini kaybetmesini engelle (kazara lockout'a karşı)
    if (
        user.id == current_user.id
        and payload.role is not None
        and payload.role != UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kendi admin rolünü kaldıramazsın.",
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "name" and isinstance(value, str):
            value = value.strip()
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    baby_count = (
        db.scalar(select(func.count(Baby.id)).where(Baby.owner_id == user.id)) or 0
    )
    return _user_out(user, baby_count)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Kullanıcıyı sil (CASCADE: bebek + içerik temizlenir)",
)
def delete_user(
    user_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    _require_admin(current_user)

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı."
        )
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kendi hesabını silemezsin.",
        )
    db.delete(user)
    db.commit()


# --------------------------- Stats --------------------------------------


@router.get(
    "/stats",
    response_model=AdminStats,
    summary="Platform istatistikleri",
)
def get_stats(current_user: CurrentUser, db: DbSession) -> AdminStats:
    _require_admin(current_user)

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    def count(stmt):
        return db.scalar(stmt) or 0

    return AdminStats(
        total_users=count(select(func.count(User.id))),
        active_users=count(select(func.count(User.id)).where(User.is_active.is_(True))),
        premium_users=count(select(func.count(User.id)).where(User.plan == "premium")),
        admin_users=count(select(func.count(User.id)).where(User.role == "admin")),
        new_users_last_7_days=count(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        ),
        total_babies=count(select(func.count(Baby.id))),
        total_journal_entries=count(select(func.count(JournalEntry.id))),
        total_media=count(select(func.count(MediaAsset.id))),
        total_community_posts=count(select(func.count(CommunityPost.id))),
        expert_posts=count(
            select(func.count(CommunityPost.id)).where(
                CommunityPost.is_expert.is_(True)
            )
        ),
        total_community_comments=count(select(func.count(CommunityComment.id))),
    )
