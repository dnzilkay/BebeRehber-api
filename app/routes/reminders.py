from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.baby import Baby
from app.models.reminder import Reminder, ReminderKind
from app.schemas.reminder import ReminderCreate, ReminderOut, ReminderUpdate


router = APIRouter(prefix="/babies/{baby_id}/reminders", tags=["reminders"])


def _ensure_owned_baby(db, user_id: int, baby_id: int) -> None:
    baby = db.get(Baby, baby_id)
    if baby is None or baby.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bebek bulunamadı.",
        )


def _get_owned_reminder(db, user_id: int, baby_id: int, rid: int) -> Reminder:
    _ensure_owned_baby(db, user_id, baby_id)
    reminder = db.get(Reminder, rid)
    if reminder is None or reminder.baby_id != baby_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hatırlatıcı bulunamadı.",
        )
    return reminder


@router.get(
    "",
    response_model=list[ReminderOut],
    summary="Bebek için hatırlatıcılar",
)
def list_reminders(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
    upcoming: bool = Query(default=False, description="Sadece tamamlanmamış"),
    kind: ReminderKind | None = Query(default=None),
) -> list[Reminder]:
    _ensure_owned_baby(db, current_user.id, baby_id)

    stmt = select(Reminder).where(Reminder.baby_id == baby_id)
    if upcoming:
        stmt = stmt.where(Reminder.completed_at.is_(None))
    if kind is not None:
        stmt = stmt.where(Reminder.kind == kind)
    stmt = stmt.order_by(Reminder.due_at.asc())

    return list(db.execute(stmt).scalars().all())


@router.post(
    "",
    response_model=ReminderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Hatırlatıcı oluştur",
)
def create_reminder(
    baby_id: int,
    payload: ReminderCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Reminder:
    _ensure_owned_baby(db, current_user.id, baby_id)

    reminder = Reminder(
        baby_id=baby_id,
        title=payload.title.strip(),
        kind=payload.kind,
        due_at=payload.due_at,
        note=payload.note,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.patch(
    "/{reminder_id}",
    response_model=ReminderOut,
    summary="Hatırlatıcı güncelle / tamamla",
)
def update_reminder(
    baby_id: int,
    reminder_id: int,
    payload: ReminderUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Reminder:
    reminder = _get_owned_reminder(db, current_user.id, baby_id, reminder_id)

    data = payload.model_dump(exclude_unset=True)
    if "completed" in data:
        completed = data.pop("completed")
        reminder.completed_at = datetime.now(timezone.utc) if completed else None
    for field, value in data.items():
        if field == "title" and isinstance(value, str):
            value = value.strip()
        setattr(reminder, field, value)

    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hatırlatıcıyı sil",
)
def delete_reminder(
    baby_id: int,
    reminder_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    reminder = _get_owned_reminder(db, current_user.id, baby_id, reminder_id)
    db.delete(reminder)
    db.commit()
