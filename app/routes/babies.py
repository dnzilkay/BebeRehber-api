from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.baby_access import ensure_baby_access, ensure_baby_owner
from app.core.deps import CurrentUser, DbSession
from app.models.baby import Baby
from app.models.baby_member import BabyMember, BabyMemberRole
from app.schemas.baby import BabyCreate, BabyOut, BabyUpdate


router = APIRouter(prefix="/babies", tags=["babies"])


@router.get(
    "",
    response_model=list[BabyOut],
    summary="Kullanıcının erişimi olan tüm bebek profilleri (owner + co-parent)",
)
def list_babies(current_user: CurrentUser, db: DbSession) -> list[Baby]:
    rows = (
        db.execute(
            select(Baby)
            .join(BabyMember, BabyMember.baby_id == Baby.id)
            .where(BabyMember.user_id == current_user.id)
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
    db.flush()  # baby.id'yi al

    # Otomatik owner kaydı
    db.add(
        BabyMember(
            baby_id=baby.id,
            user_id=current_user.id,
            role=BabyMemberRole.OWNER,
        )
    )
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
    return ensure_baby_access(db, current_user.id, baby_id)


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
    baby = ensure_baby_access(db, current_user.id, baby_id)

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
    summary="Bebek profilini sil (owner only)",
)
def delete_baby(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    baby = ensure_baby_owner(db, current_user.id, baby_id)
    db.delete(baby)
    db.commit()
