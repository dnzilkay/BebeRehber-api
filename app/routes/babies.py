from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.baby import Baby
from app.schemas.baby import BabyCreate, BabyOut, BabyUpdate


router = APIRouter(prefix="/babies", tags=["babies"])


def _get_owned_baby(db, user_id: int, baby_id: int) -> Baby:
    baby = db.get(Baby, baby_id)
    if baby is None or baby.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bebek bulunamadı.",
        )
    return baby


@router.get(
    "",
    response_model=list[BabyOut],
    summary="Mevcut kullanıcının bebek listesi",
)
def list_babies(current_user: CurrentUser, db: DbSession) -> list[Baby]:
    rows = (
        db.execute(
            select(Baby)
            .where(Baby.owner_id == current_user.id)
            .order_by(Baby.created_at.asc())
        )
        .scalars()
        .all()
    )
    return list(rows)


@router.post(
    "",
    response_model=BabyOut,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni bebek profili oluştur",
)
def create_baby(
    payload: BabyCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Baby:
    baby = Baby(
        owner_id=current_user.id,
        name=payload.name.strip(),
        birth_date=payload.birth_date,
        gender=payload.gender,
        avatar_url=payload.avatar_url,
    )
    db.add(baby)
    db.commit()
    db.refresh(baby)
    return baby


@router.get(
    "/{baby_id}",
    response_model=BabyOut,
    summary="Bebek profili detay",
)
def get_baby(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Baby:
    return _get_owned_baby(db, current_user.id, baby_id)


@router.patch(
    "/{baby_id}",
    response_model=BabyOut,
    summary="Bebek profilini güncelle",
)
def update_baby(
    baby_id: int,
    payload: BabyUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Baby:
    baby = _get_owned_baby(db, current_user.id, baby_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "name" and isinstance(value, str):
            value = value.strip()
        setattr(baby, field, value)

    db.commit()
    db.refresh(baby)
    return baby


@router.delete(
    "/{baby_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bebek profilini sil",
)
def delete_baby(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    baby = _get_owned_baby(db, current_user.id, baby_id)
    db.delete(baby)
    db.commit()
