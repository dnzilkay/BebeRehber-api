from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.baby_access import ensure_baby_access
from app.core.deps import CurrentUser, DbSession
from app.models.care_log import CareKind, CareLog
from app.schemas.care_log import CareLogCreate, CareLogOut, CareSummary


router = APIRouter(prefix="/babies/{baby_id}/care-logs", tags=["care-logs"])


@router.get(
    "",
    response_model=list[CareLogOut],
    summary="Bebek için bakım kayıtları (filtreli)",
)
def list_care_logs(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
    kind: CareKind | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=365),
) -> list[CareLog]:
    ensure_baby_access(db, current_user.id, baby_id)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(CareLog)
        .where(CareLog.baby_id == baby_id)
        .where(CareLog.started_at >= cutoff)
    )
    if kind is not None:
        stmt = stmt.where(CareLog.kind == kind)
    stmt = stmt.order_by(CareLog.started_at.desc())

    return list(db.execute(stmt).scalars().all())


@router.post(
    "",
    response_model=CareLogOut,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni bakım kaydı oluştur",
)
def create_care_log(
    baby_id: int,
    payload: CareLogCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> CareLog:
    ensure_baby_access(db, current_user.id, baby_id)

    log = CareLog(
        baby_id=baby_id,
        kind=payload.kind,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        amount_ml=payload.amount_ml,
        diaper_type=payload.diaper_type,
        note=payload.note,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.delete(
    "/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bakım kaydını sil",
)
def delete_care_log(
    baby_id: int,
    log_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    ensure_baby_access(db, current_user.id, baby_id)
    log = db.get(CareLog, log_id)
    if log is None or log.baby_id != baby_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kayıt bulunamadı.",
        )
    db.delete(log)
    db.commit()


@router.get(
    "/summary",
    response_model=CareSummary,
    summary="Günlük bakım özeti (son N gün)",
)
def care_summary(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
    days: int = Query(default=1, ge=1, le=30),
) -> CareSummary:
    ensure_baby_access(db, current_user.id, baby_id)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    base = select(CareLog).where(
        CareLog.baby_id == baby_id, CareLog.started_at >= cutoff
    )

    sleep_logs = list(
        db.execute(base.where(CareLog.kind == CareKind.SLEEP)).scalars().all()
    )
    sleep_minutes = sum(
        int((log.ended_at - log.started_at).total_seconds() // 60)
        for log in sleep_logs
        if log.ended_at is not None
    )

    feeding_count = (
        db.execute(
            select(func.count())
            .select_from(CareLog)
            .where(
                CareLog.baby_id == baby_id,
                CareLog.kind == CareKind.FEEDING,
                CareLog.started_at >= cutoff,
            )
        ).scalar()
        or 0
    )
    feeding_total_ml = (
        db.execute(
            select(func.coalesce(func.sum(CareLog.amount_ml), 0)).where(
                CareLog.baby_id == baby_id,
                CareLog.kind == CareKind.FEEDING,
                CareLog.started_at >= cutoff,
            )
        ).scalar()
        or 0
    )
    diaper_count = (
        db.execute(
            select(func.count())
            .select_from(CareLog)
            .where(
                CareLog.baby_id == baby_id,
                CareLog.kind == CareKind.DIAPER,
                CareLog.started_at >= cutoff,
            )
        ).scalar()
        or 0
    )

    return CareSummary(
        sleep_minutes=int(sleep_minutes),
        feeding_count=int(feeding_count),
        feeding_total_ml=int(feeding_total_ml),
        diaper_count=int(diaper_count),
    )
