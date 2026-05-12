from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core import storage
from app.core.deps import CurrentUser, DbSession
from app.models.album import Album
from app.models.baby import Baby
from app.models.journal_entry import JournalEntry
from app.schemas.album import AlbumCreate, AlbumOut, AlbumUpdate


router = APIRouter(prefix="/babies/{baby_id}/albums", tags=["albums"])


def _ensure_owned_baby(db, user_id: int, baby_id: int) -> None:
    baby = db.get(Baby, baby_id)
    if baby is None or baby.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bebek bulunamadı.",
        )


def _get_owned_album(db, user_id: int, baby_id: int, album_id: int) -> Album:
    _ensure_owned_baby(db, user_id, baby_id)
    album = db.get(Album, album_id)
    if album is None or album.baby_id != baby_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Albüm bulunamadı.",
        )
    return album


def _album_out(album: Album, entries_count: int) -> AlbumOut:
    return AlbumOut(
        id=album.id,
        baby_id=album.baby_id,
        name=album.name,
        cover_url=storage.public_url(album.cover_object_key)
        if album.cover_object_key
        else None,
        entries_count=entries_count,
        created_at=album.created_at,
    )


@router.get("", response_model=list[AlbumOut], summary="Albümleri listele")
def list_albums(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> list[AlbumOut]:
    _ensure_owned_baby(db, current_user.id, baby_id)

    stmt = (
        select(Album, func.count(JournalEntry.id))
        .outerjoin(JournalEntry, JournalEntry.album_id == Album.id)
        .where(Album.baby_id == baby_id)
        .group_by(Album.id)
        .order_by(Album.created_at.desc(), Album.id.desc())
    )
    rows = db.execute(stmt).all()
    return [_album_out(album, count) for album, count in rows]


@router.post(
    "",
    response_model=AlbumOut,
    status_code=status.HTTP_201_CREATED,
    summary="Albüm oluştur",
)
def create_album(
    baby_id: int,
    payload: AlbumCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> AlbumOut:
    _ensure_owned_baby(db, current_user.id, baby_id)

    album = Album(baby_id=baby_id, name=payload.name.strip())
    db.add(album)
    db.commit()
    db.refresh(album)
    return _album_out(album, entries_count=0)


@router.patch("/{album_id}", response_model=AlbumOut, summary="Albüm güncelle")
def update_album(
    baby_id: int,
    album_id: int,
    payload: AlbumUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> AlbumOut:
    album = _get_owned_album(db, current_user.id, baby_id, album_id)

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "name" and isinstance(value, str):
            value = value.strip()
        setattr(album, field, value)

    db.commit()
    db.refresh(album)
    count = db.scalar(
        select(func.count(JournalEntry.id)).where(JournalEntry.album_id == album.id)
    )
    return _album_out(album, entries_count=count or 0)


@router.delete(
    "/{album_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Albümü sil (entry'ler bağımsız kalır)",
)
def delete_album(
    baby_id: int,
    album_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    album = _get_owned_album(db, current_user.id, baby_id, album_id)
    db.delete(album)
    db.commit()
