from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.baby_access import ensure_baby_access
from app.core.deps import CurrentUser, DbSession
from app.core.limits import clamp_history_days_for_baby
from app.models.milestone import Milestone, MilestoneCategory
from app.schemas.milestone import MilestoneCreate, MilestoneOut, MilestoneUpdate


router = APIRouter(prefix="/babies/{baby_id}/milestones", tags=["milestones"])


def _get_owned_milestone(db, user_id: int, baby_id: int, mid: int) -> Milestone:
    ensure_baby_access(db, user_id, baby_id)
    milestone = db.get(Milestone, mid)
    if milestone is None or milestone.baby_id != baby_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gelişim notu bulunamadı.",
        )
    return milestone


@router.get(
    "",
    response_model=list[MilestoneOut],
    summary="Bebek için gelişim notları (milestone)",
)
def list_milestones(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
    category: MilestoneCategory | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=200),
    days: int | None = Query(
        default=None,
        ge=1,
        le=365,
        description="Son N gün penceresi; plan tavanı uygulanır (Free 14 / Premium 365).",
    ),
) -> list[Milestone]:
    ensure_baby_access(db, current_user.id, baby_id)

    stmt = select(Milestone).where(Milestone.baby_id == baby_id)
    if days is not None:
        effective_days = clamp_history_days_for_baby(db, current_user, baby_id, days)
        cutoff = date.today() - timedelta(days=effective_days)
        stmt = stmt.where(Milestone.reached_on >= cutoff)
    if category is not None:
        stmt = stmt.where(Milestone.category == category)
    stmt = stmt.order_by(Milestone.reached_on.desc(), Milestone.id.desc())
    if limit is not None:
        stmt = stmt.limit(limit)

    return list(db.execute(stmt).scalars().all())


@router.post(
    "",
    response_model=MilestoneOut,
    status_code=status.HTTP_201_CREATED,
    summary="Gelişim notu oluştur",
)
def create_milestone(
    baby_id: int,
    payload: MilestoneCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Milestone:
    ensure_baby_access(db, current_user.id, baby_id)

    milestone = Milestone(
        baby_id=baby_id,
        preset_id=payload.preset_id,
        title=payload.title.strip(),
        category=payload.category,
        reached_on=payload.reached_on,
        note=payload.note,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


@router.patch(
    "/{milestone_id}",
    response_model=MilestoneOut,
    summary="Gelişim notu güncelle",
)
def update_milestone(
    baby_id: int,
    milestone_id: int,
    payload: MilestoneUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Milestone:
    milestone = _get_owned_milestone(db, current_user.id, baby_id, milestone_id)

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "title" and isinstance(value, str):
            value = value.strip()
        setattr(milestone, field, value)

    db.commit()
    db.refresh(milestone)
    return milestone


@router.delete(
    "/{milestone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Gelişim notunu sil",
)
def delete_milestone(
    baby_id: int,
    milestone_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    milestone = _get_owned_milestone(db, current_user.id, baby_id, milestone_id)
    db.delete(milestone)
    db.commit()
