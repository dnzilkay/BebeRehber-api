"""Public rehber yazıları (BACKLOG #2) — herkese açık liste/detay, admin CRUD.

Hamilelik ve bebek gelişimi bilgilendirici içerikleri için CMS. Free dahil
tüm kullanıcılar (login bile gerekmez) okuyabilir; sadece admin yazabilir.
"""

import re
import unicodedata

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import AdminUser, DbSession
from app.models.guide_article import GuideArticle, GuideCategory
from app.schemas.guide_article import (
    GuideArticleCreate,
    GuideArticleOut,
    GuideArticleSummary,
    GuideArticleUpdate,
)


router = APIRouter(prefix="/guides", tags=["guides"])


# ---- Slug üretimi --------------------------------------------------------

_TR_MAP = str.maketrans(
    {
        "ç": "c",
        "Ç": "c",
        "ğ": "g",
        "Ğ": "g",
        "ı": "i",
        "İ": "i",
        "ö": "o",
        "Ö": "o",
        "ş": "s",
        "Ş": "s",
        "ü": "u",
        "Ü": "u",
    }
)


def _slugify(text: str) -> str:
    text = text.translate(_TR_MAP)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:160] or "rehber"


def _ensure_unique_slug(db, base: str, exclude_id: int | None = None) -> str:
    """Slug çakışırsa -2, -3 ... ekleyerek benzersizleştir."""
    candidate = base
    suffix = 2
    while True:
        stmt = select(GuideArticle).where(GuideArticle.slug == candidate)
        if exclude_id is not None:
            stmt = stmt.where(GuideArticle.id != exclude_id)
        if db.execute(stmt).scalar_one_or_none() is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


# ---- Public endpoint'ler -------------------------------------------------


@router.get(
    "",
    response_model=list[GuideArticleSummary],
    summary="Rehber yazıları (herkese açık)",
)
def list_guides(
    db: DbSession,
    category: GuideCategory | None = Query(default=None),
) -> list[GuideArticle]:
    stmt = select(GuideArticle)
    if category is not None:
        stmt = stmt.where(GuideArticle.category == category)
    stmt = stmt.order_by(GuideArticle.created_at.desc())
    return list(db.execute(stmt).scalars().all())


@router.get(
    "/{slug}",
    response_model=GuideArticleOut,
    summary="Rehber yazı detayı (slug ile)",
)
def get_guide(slug: str, db: DbSession) -> GuideArticle:
    row = db.execute(
        select(GuideArticle).where(GuideArticle.slug == slug)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rehber yazısı bulunamadı.",
        )
    return row


# ---- Admin CRUD ----------------------------------------------------------


@router.post(
    "",
    response_model=GuideArticleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni rehber yazısı (admin)",
)
def create_guide(
    payload: GuideArticleCreate,
    current_user: AdminUser,
    db: DbSession,
) -> GuideArticle:
    base_slug = _slugify(payload.slug or payload.title)
    slug = _ensure_unique_slug(db, base_slug)
    article = GuideArticle(
        author_id=current_user.id,
        slug=slug,
        title=payload.title.strip(),
        summary=payload.summary.strip(),
        body=payload.body,
        category=payload.category,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.patch(
    "/{guide_id}",
    response_model=GuideArticleOut,
    summary="Rehber yazısını güncelle (admin)",
)
def update_guide(
    guide_id: int,
    payload: GuideArticleUpdate,
    current_user: AdminUser,
    db: DbSession,
) -> GuideArticle:
    article = db.get(GuideArticle, guide_id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rehber yazısı bulunamadı.",
        )
    data = payload.model_dump(exclude_unset=True)
    if "title" in data and data["title"]:
        # Slug'ı title değiştiğinde güncelle (kullanıcı bilinçli karar değil)
        article.slug = _ensure_unique_slug(
            db, _slugify(data["title"]), exclude_id=article.id
        )
    for field, value in data.items():
        if field in ("title", "summary") and isinstance(value, str):
            value = value.strip()
        setattr(article, field, value)
    db.commit()
    db.refresh(article)
    return article


@router.delete(
    "/{guide_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Rehber yazısını sil (admin)",
)
def delete_guide(
    guide_id: int,
    current_user: AdminUser,
    db: DbSession,
) -> None:
    article = db.get(GuideArticle, guide_id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rehber yazısı bulunamadı.",
        )
    db.delete(article)
    db.commit()
