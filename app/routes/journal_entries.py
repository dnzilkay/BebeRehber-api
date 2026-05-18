from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core import storage
from app.core.baby_access import ensure_baby_access
from app.core.deps import CurrentUser, DbSession
from app.core.limits import clamp_history_days_for_baby
from app.models.album import Album
from app.models.journal_entry import JournalEntry
from app.models.media_asset import MediaAsset
from app.schemas.journal_entry import (
    JournalEntryCreate,
    JournalEntryOut,
    JournalEntryUpdate,
)
from app.schemas.media_asset import MediaAssetOut


router = APIRouter(prefix="/babies/{baby_id}/entries", tags=["journal-entries"])


def _ensure_album_owned(db, baby_id: int, album_id: int | None) -> None:
    if album_id is None:
        return
    album = db.get(Album, album_id)
    if album is None or album.baby_id != baby_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Albüm bulunamadı.",
        )


def _get_owned_entry(db, user_id: int, baby_id: int, entry_id: int) -> JournalEntry:
    ensure_baby_access(db, user_id, baby_id)
    entry = db.get(JournalEntry, entry_id)
    if entry is None or entry.baby_id != baby_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Günlük girişi bulunamadı.",
        )
    return entry


def _media_out(m: MediaAsset) -> MediaAssetOut:
    return MediaAssetOut(
        id=m.id,
        entry_id=m.entry_id,
        kind=m.kind,
        content_type=m.content_type,
        size_bytes=m.size_bytes,
        duration_sec=m.duration_sec,
        url=storage.public_url(m.object_key),
        created_at=m.created_at,
    )


def _entry_out(entry: JournalEntry) -> JournalEntryOut:
    return JournalEntryOut(
        id=entry.id,
        baby_id=entry.baby_id,
        album_id=entry.album_id,
        title=entry.title,
        body=entry.body,
        occurred_on=entry.occurred_on,
        created_at=entry.created_at,
        media=[_media_out(m) for m in entry.media],
    )


@router.get("", response_model=list[JournalEntryOut], summary="Günlük girişleri")
def list_entries(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
    album_id: int | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=500),
    days: int | None = Query(
        default=None,
        ge=1,
        le=365,
        description="Son N gün penceresi; plan tavanı uygulanır (Free 14 / Premium 365).",
    ),
) -> list[JournalEntryOut]:
    ensure_baby_access(db, current_user.id, baby_id)

    stmt = select(JournalEntry).where(JournalEntry.baby_id == baby_id)
    if days is not None:
        effective_days = clamp_history_days_for_baby(db, current_user, baby_id, days)
        cutoff = date.today() - timedelta(days=effective_days)
        stmt = stmt.where(JournalEntry.occurred_on >= cutoff)
    if album_id is not None:
        stmt = stmt.where(JournalEntry.album_id == album_id)
    stmt = stmt.order_by(
        JournalEntry.occurred_on.desc(),
        JournalEntry.id.desc(),
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    rows = list(db.execute(stmt).scalars().all())
    return [_entry_out(e) for e in rows]


@router.post(
    "",
    response_model=JournalEntryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Günlük girişi oluştur",
)
def create_entry(
    baby_id: int,
    payload: JournalEntryCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> JournalEntryOut:
    ensure_baby_access(db, current_user.id, baby_id)
    _ensure_album_owned(db, baby_id, payload.album_id)

    entry = JournalEntry(
        baby_id=baby_id,
        album_id=payload.album_id,
        title=payload.title.strip(),
        body=payload.body,
        occurred_on=payload.occurred_on,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _entry_out(entry)


@router.patch(
    "/{entry_id}", response_model=JournalEntryOut, summary="Günlük girişini güncelle"
)
def update_entry(
    baby_id: int,
    entry_id: int,
    payload: JournalEntryUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> JournalEntryOut:
    entry = _get_owned_entry(db, current_user.id, baby_id, entry_id)

    data = payload.model_dump(exclude_unset=True)
    if "album_id" in data:
        _ensure_album_owned(db, baby_id, data["album_id"])
    for field, value in data.items():
        if field == "title" and isinstance(value, str):
            value = value.strip()
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)
    return _entry_out(entry)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Günlük girişini sil (media dahil)",
)
def delete_entry(
    baby_id: int,
    entry_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    entry = _get_owned_entry(db, current_user.id, baby_id, entry_id)
    # storage'daki medya dosyalarını da temizle
    for m in entry.media:
        storage.delete_object(m.object_key)
    db.delete(entry)
    db.commit()
