"""Sosyal Medya Yönetimi — admin paneli marka içerik takvimi.

Admin role'üne sahip kullanıcılar BebeRehber markası için içerik
planlar, yayın takvimi tutar ve yayın sonrası etkileşim metriklerini
manuel olarak günceller.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.models.social_post import SocialPlatform, SocialPost, SocialPostStatus
from app.models.user import User, UserRole
from app.schemas.social import (
    SocialPostCreate,
    SocialPostOut,
    SocialPostUpdate,
    SocialStatsOut,
)


router = APIRouter(prefix="/admin/social-posts", tags=["social"])


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu modül yalnızca yöneticilere açıktır.",
        )


def _maybe_publish_now(post: SocialPost) -> None:
    """Status published'a çevrildiyse published_at'ı setle."""
    if post.status == SocialPostStatus.PUBLISHED and post.published_at is None:
        post.published_at = datetime.now(timezone.utc)


# ------------------------------ list ------------------------------------


@router.get(
    "",
    response_model=list[SocialPostOut],
    summary="Sosyal medya içerik listesi (filtreli)",
)
def list_posts(
    current_user: CurrentUser,
    db: DbSession,
    platform: SocialPlatform | None = Query(default=None),
    status_filter: SocialPostStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[SocialPost]:
    _require_admin(current_user)

    stmt = select(SocialPost)
    if platform is not None:
        stmt = stmt.where(SocialPost.platform == platform)
    if status_filter is not None:
        stmt = stmt.where(SocialPost.status == status_filter)
    # En yeni başta — yayınlanmış için published_at, taslak/planlı için
    # scheduled_for veya created_at sıralaması işe karışık olmasın diye
    # basit tutuyoruz: created_at desc
    stmt = stmt.order_by(
        SocialPost.scheduled_for.desc().nullslast(),
        SocialPost.created_at.desc(),
    ).limit(limit)

    return list(db.execute(stmt).scalars().all())


# ----------------------------- create ----------------------------------


@router.post(
    "",
    response_model=SocialPostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni sosyal medya içeriği oluştur",
)
def create_post(
    payload: SocialPostCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> SocialPost:
    _require_admin(current_user)

    post = SocialPost(
        author_id=current_user.id,
        platform=payload.platform,
        title=payload.title.strip(),
        body=payload.body,
        image_url=payload.image_url,
        scheduled_for=payload.scheduled_for,
        status=payload.status,
    )
    _maybe_publish_now(post)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


# ----------------------------- update ----------------------------------


@router.patch(
    "/{post_id}",
    response_model=SocialPostOut,
    summary="İçeriği güncelle (status / engagement / scheduled_for)",
)
def update_post(
    post_id: int,
    payload: SocialPostUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> SocialPost:
    _require_admin(current_user)

    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="İçerik bulunamadı."
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "title" and isinstance(value, str):
            value = value.strip()
        setattr(post, field, value)
    _maybe_publish_now(post)

    db.commit()
    db.refresh(post)
    return post


# ----------------------------- delete ----------------------------------


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="İçeriği sil",
)
def delete_post(
    post_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    _require_admin(current_user)
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="İçerik bulunamadı."
        )
    db.delete(post)
    db.commit()


# ------------------------------ stats ----------------------------------


@router.get(
    "/stats",
    response_model=SocialStatsOut,
    summary="Sosyal medya özet istatistikleri",
)
def get_stats(current_user: CurrentUser, db: DbSession) -> SocialStatsOut:
    _require_admin(current_user)

    def count_by(s: SocialPostStatus) -> int:
        return (
            db.scalar(select(func.count(SocialPost.id)).where(SocialPost.status == s))
            or 0
        )

    total_posts = db.scalar(select(func.count(SocialPost.id))) or 0
    total_reach = db.scalar(select(func.coalesce(func.sum(SocialPost.reach), 0))) or 0
    total_engagement = (
        db.scalar(
            select(
                func.coalesce(
                    func.sum(
                        SocialPost.likes + SocialPost.comments_count + SocialPost.shares
                    ),
                    0,
                )
            )
        )
        or 0
    )

    return SocialStatsOut(
        total_posts=int(total_posts),
        drafts=count_by(SocialPostStatus.DRAFT),
        scheduled=count_by(SocialPostStatus.SCHEDULED),
        published=count_by(SocialPostStatus.PUBLISHED),
        total_reach=int(total_reach),
        total_engagement=int(total_engagement),
    )
