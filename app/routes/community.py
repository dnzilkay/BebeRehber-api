"""Topluluk Portalı (Premium-only) — post + comment.

Premium ve admin kullanıcılar görür, oluşturur, yorum yapar.
Admin kullanıcıların oluşturduğu post'lar otomatik `is_expert=True`
(uzman içeriği). Kullanıcılar kendi post/comment'lerini silebilir;
admin tüm içeriği silebilir (moderasyon).
"""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.core.limits import is_premium
from app.models.community_comment import CommunityComment
from app.models.community_post import CommunityCategory, CommunityPost
from app.models.user import User, UserRole
from app.schemas.community import (
    CommunityAuthor,
    CommunityCommentCreate,
    CommunityCommentOut,
    CommunityPostCreate,
    CommunityPostDetailOut,
    CommunityPostOut,
)


router = APIRouter(prefix="/community", tags=["community"])


# --------------------------- access guards ------------------------------


def _require_community_access(user) -> None:
    if not is_premium(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Topluluk Portalı Premium pakette yer alır. "
                "Premium'a geçerek diğer ebeveynlerle deneyim paylaşabilirsin."
            ),
        )


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


# --------------------------- serializers --------------------------------


def _author_out(user: User) -> CommunityAuthor:
    return CommunityAuthor(id=user.id, name=user.name, role=user.role.value)


def _comment_out(c: CommunityComment, author: User) -> CommunityCommentOut:
    return CommunityCommentOut(
        id=c.id,
        post_id=c.post_id,
        body=c.body,
        author=_author_out(author),
        created_at=c.created_at,
    )


# ----------------------------- routes -----------------------------------


@router.get(
    "/posts",
    response_model=list[CommunityPostOut],
    summary="Premium: post listesi",
)
def list_posts(
    current_user: CurrentUser,
    db: DbSession,
    category: CommunityCategory | None = Query(default=None),
    expert_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[CommunityPostOut]:
    _require_community_access(current_user)

    stmt = (
        select(
            CommunityPost,
            User,
            func.count(CommunityComment.id),
        )
        .join(User, User.id == CommunityPost.author_id)
        .outerjoin(CommunityComment, CommunityComment.post_id == CommunityPost.id)
        .group_by(CommunityPost.id, User.id)
        .order_by(CommunityPost.created_at.desc(), CommunityPost.id.desc())
    )
    if category is not None:
        stmt = stmt.where(CommunityPost.category == category)
    if expert_only:
        stmt = stmt.where(CommunityPost.is_expert.is_(True))
    stmt = stmt.limit(limit)

    rows = db.execute(stmt).all()
    return [
        CommunityPostOut(
            id=p.id,
            title=p.title,
            body=p.body,
            category=p.category,
            is_expert=p.is_expert,
            comments_count=cnt or 0,
            author=_author_out(u),
            created_at=p.created_at,
        )
        for p, u, cnt in rows
    ]


@router.post(
    "/posts",
    response_model=CommunityPostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Premium: yeni post oluştur",
)
def create_post(
    payload: CommunityPostCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> CommunityPostOut:
    _require_community_access(current_user)

    post = CommunityPost(
        author_id=current_user.id,
        title=payload.title.strip(),
        body=payload.body,
        category=payload.category,
        is_expert=_is_admin(current_user),  # admin = uzman içeriği
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return CommunityPostOut(
        id=post.id,
        title=post.title,
        body=post.body,
        category=post.category,
        is_expert=post.is_expert,
        comments_count=0,
        author=_author_out(current_user),
        created_at=post.created_at,
    )


@router.get(
    "/posts/{post_id}",
    response_model=CommunityPostDetailOut,
    summary="Premium: post + yorumlar",
)
def get_post(
    post_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> CommunityPostDetailOut:
    _require_community_access(current_user)

    row = db.execute(
        select(CommunityPost, User)
        .join(User, User.id == CommunityPost.author_id)
        .where(CommunityPost.id == post_id)
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post bulunamadı."
        )
    post, post_author = row

    comment_rows = db.execute(
        select(CommunityComment, User)
        .join(User, User.id == CommunityComment.author_id)
        .where(CommunityComment.post_id == post_id)
        .order_by(CommunityComment.created_at.asc())
    ).all()

    return CommunityPostDetailOut(
        id=post.id,
        title=post.title,
        body=post.body,
        category=post.category,
        is_expert=post.is_expert,
        comments_count=len(comment_rows),
        author=_author_out(post_author),
        created_at=post.created_at,
        comments=[_comment_out(c, u) for c, u in comment_rows],
    )


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Post sil (yazar veya admin)",
)
def delete_post(
    post_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    _require_community_access(current_user)
    post = db.get(CommunityPost, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post bulunamadı."
        )
    if post.author_id != current_user.id and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sadece kendi paylaşımını silebilirsin.",
        )
    db.delete(post)
    db.commit()


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommunityCommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Premium: post'a yorum ekle",
)
def create_comment(
    post_id: int,
    payload: CommunityCommentCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> CommunityCommentOut:
    _require_community_access(current_user)

    post = db.get(CommunityPost, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post bulunamadı."
        )

    comment = CommunityComment(
        post_id=post_id,
        author_id=current_user.id,
        body=payload.body.strip(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _comment_out(comment, current_user)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Yorum sil (yazar veya admin)",
)
def delete_comment(
    comment_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    _require_community_access(current_user)
    comment = db.get(CommunityComment, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Yorum bulunamadı."
        )
    if comment.author_id != current_user.id and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sadece kendi yorumunu silebilirsin.",
        )
    db.delete(comment)
    db.commit()
