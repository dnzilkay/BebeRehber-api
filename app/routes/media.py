import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import func, select

from app.core import storage, video
from app.core.deps import CurrentUser, DbSession
from app.core.limits import FREE_MAX_MEDIA_PER_ALBUM, is_premium, max_video_seconds
from app.models.baby import Baby
from app.models.journal_entry import JournalEntry
from app.models.media_asset import MediaAsset, MediaKind
from app.schemas.media_asset import MediaAssetOut


router = APIRouter(prefix="/babies/{baby_id}/entries/{entry_id}/media", tags=["media"])


def _get_owned_entry(db, user_id: int, baby_id: int, entry_id: int) -> JournalEntry:
    baby = db.get(Baby, baby_id)
    if baby is None or baby.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bebek bulunamadı.",
        )
    entry = db.get(JournalEntry, entry_id)
    if entry is None or entry.baby_id != baby_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Günlük girişi bulunamadı.",
        )
    return entry


def _kind_for(content_type: str) -> MediaKind:
    if content_type.startswith("image/"):
        return MediaKind.IMAGE
    if content_type.startswith("video/"):
        return MediaKind.VIDEO
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Sadece görsel veya video yüklenebilir.",
    )


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


def _enforce_album_media_limit(db, entry: JournalEntry, user) -> None:
    """Free pakette albüm başına en fazla FREE_MAX_MEDIA_PER_ALBUM medya."""
    if is_premium(user):
        return
    if entry.album_id is None:
        return
    count = (
        db.scalar(
            select(func.count(MediaAsset.id))
            .join(JournalEntry, MediaAsset.entry_id == JournalEntry.id)
            .where(JournalEntry.album_id == entry.album_id)
        )
        or 0
    )
    if count >= FREE_MAX_MEDIA_PER_ALBUM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Free pakette albüm başına en fazla {FREE_MAX_MEDIA_PER_ALBUM} "
                "medya yükleyebilirsin. Sınırsız medya için Premium'a geç."
            ),
        )


def _enforce_video_duration(user, duration_sec: int | None) -> None:
    if duration_sec is None:
        # ffprobe yoksa veya parse edilemediyse Free'de güvenli tarafa çek
        if not is_premium(user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video süresi tespit edilemedi; lütfen tekrar dene.",
            )
        return
    limit = max_video_seconds(user)
    if duration_sec > limit:
        plan_word = "Premium" if is_premium(user) else "Free"
        upsell = "" if is_premium(user) else " Daha uzun videolar için Premium'a geç."
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"{plan_word} pakette video en fazla {limit} saniye olabilir "
                f"(yüklenen: {duration_sec} sn).{upsell}"
            ),
        )


@router.post(
    "",
    response_model=MediaAssetOut,
    status_code=status.HTTP_201_CREATED,
    summary="Medya yükle (foto / video)",
)
async def upload_media(
    baby_id: int,
    entry_id: int,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> MediaAssetOut:
    entry = _get_owned_entry(db, current_user.id, baby_id, entry_id)

    content_type = file.content_type or "application/octet-stream"
    kind = _kind_for(content_type)

    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya boş.",
        )

    _enforce_album_media_limit(db, entry, current_user)

    duration_sec: int | None = None
    if kind == MediaKind.VIDEO:
        suffix = Path(file.filename or "").suffix.lower()
        duration_sec = video.probe_duration_seconds(data, suffix=suffix)
        _enforce_video_duration(current_user, duration_sec)

    suffix = Path(file.filename or "").suffix.lower()
    object_key = f"journal/{baby_id}/{entry_id}/{uuid.uuid4().hex}{suffix}"
    storage.upload_bytes(object_key, data, content_type)

    media = MediaAsset(
        entry_id=entry.id,
        object_key=object_key,
        kind=kind,
        content_type=content_type,
        size_bytes=len(data),
        duration_sec=duration_sec,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return _media_out(media)


@router.delete(
    "/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Medyayı sil",
)
def delete_media(
    baby_id: int,
    entry_id: int,
    media_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    entry = _get_owned_entry(db, current_user.id, baby_id, entry_id)
    media = db.get(MediaAsset, media_id)
    if media is None or media.entry_id != entry.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medya bulunamadı.",
        )
    storage.delete_object(media.object_key)
    db.delete(media)
    db.commit()
