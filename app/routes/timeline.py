"""Premium-only birleşik zaman tüneli: günlük girişleri + milestone'lar."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core import storage
from app.core.deps import CurrentUser, DbSession
from app.core.limits import is_premium
from app.models.album import Album
from app.models.baby import Baby
from app.models.journal_entry import JournalEntry
from app.models.media_asset import MediaAsset
from app.models.milestone import Milestone
from app.schemas.media_asset import MediaAssetOut
from app.schemas.timeline import TimelineEntry, TimelineItem, TimelineMilestone


router = APIRouter(prefix="/babies/{baby_id}/timeline", tags=["timeline"])


def _ensure_owned_baby(db, user_id: int, baby_id: int) -> None:
    baby = db.get(Baby, baby_id)
    if baby is None or baby.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bebek bulunamadı.",
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


@router.get(
    "",
    response_model=list[TimelineItem],
    summary="Premium: birleşik kronolojik timeline",
)
def get_timeline(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> list[TimelineItem]:
    _ensure_owned_baby(db, current_user.id, baby_id)

    if not is_premium(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Timeline görünümü Premium pakette yer alır. "
                "Premium'a geçerek tüm anıların kronolojik akışını gör."
            ),
        )

    entries = list(
        db.execute(
            select(JournalEntry).where(JournalEntry.baby_id == baby_id)
        ).scalars()
    )
    milestones = list(
        db.execute(select(Milestone).where(Milestone.baby_id == baby_id)).scalars()
    )

    # Albüm isimlerini tek seferde çek
    album_names: dict[int, str] = {}
    if entries:
        album_ids = {e.album_id for e in entries if e.album_id is not None}
        if album_ids:
            for a in db.execute(select(Album).where(Album.id.in_(album_ids))).scalars():
                album_names[a.id] = a.name

    items: list[TimelineItem] = []
    for e in entries:
        items.append(
            TimelineEntry(
                id=e.id,
                date=e.occurred_on,
                title=e.title,
                body=e.body,
                album_id=e.album_id,
                album_name=album_names.get(e.album_id) if e.album_id else None,
                media=[_media_out(m) for m in e.media],
                created_at=e.created_at,
            )
        )
    for m in milestones:
        items.append(
            TimelineMilestone(
                id=m.id,
                date=m.reached_on,
                title=m.title,
                category=m.category,
                preset_id=m.preset_id,
                note=m.note,
                created_at=m.created_at,
            )
        )

    # En yeni başta
    items.sort(key=lambda it: (it.date, it.created_at), reverse=True)
    return items
