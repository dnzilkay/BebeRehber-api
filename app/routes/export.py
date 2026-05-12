"""Premium-only bulut yedek: bebek verisini ZIP olarak dışa aktarır."""

import io
import json
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.core import storage
from app.core.deps import CurrentUser, DbSession
from app.core.limits import is_premium
from app.models.album import Album
from app.models.baby import Baby
from app.models.care_log import CareLog
from app.models.journal_entry import JournalEntry
from app.models.milestone import Milestone
from app.models.reminder import Reminder


router = APIRouter(prefix="/babies/{baby_id}/export", tags=["export"])


def _ensure_owned_baby(db, user_id: int, baby_id: int) -> Baby:
    baby = db.get(Baby, baby_id)
    if baby is None or baby.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bebek bulunamadı.",
        )
    return baby


def _iso(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _baby_dict(baby: Baby) -> dict:
    return {
        "id": baby.id,
        "name": baby.name,
        "birth_date": _iso(baby.birth_date),
        "gender": baby.gender.value if hasattr(baby.gender, "value") else baby.gender,
        "created_at": _iso(baby.created_at),
    }


def _album_dict(a: Album) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "cover_object_key": a.cover_object_key,
        "created_at": _iso(a.created_at),
    }


def _entry_dict(e: JournalEntry) -> dict:
    return {
        "id": e.id,
        "album_id": e.album_id,
        "title": e.title,
        "body": e.body,
        "occurred_on": _iso(e.occurred_on),
        "created_at": _iso(e.created_at),
        "media": [
            {
                "id": m.id,
                "kind": m.kind.value if hasattr(m.kind, "value") else m.kind,
                "object_key": m.object_key,
                "content_type": m.content_type,
                "size_bytes": m.size_bytes,
                "duration_sec": m.duration_sec,
                "created_at": _iso(m.created_at),
            }
            for m in e.media
        ],
    }


def _milestone_dict(m: Milestone) -> dict:
    return {
        "id": m.id,
        "preset_id": m.preset_id,
        "title": m.title,
        "category": m.category.value if hasattr(m.category, "value") else m.category,
        "reached_on": _iso(m.reached_on),
        "note": m.note,
        "created_at": _iso(m.created_at),
    }


def _care_log_dict(c: CareLog) -> dict:
    return {
        "id": c.id,
        "kind": c.kind.value if hasattr(c.kind, "value") else c.kind,
        "started_at": _iso(c.started_at),
        "ended_at": _iso(c.ended_at),
        "amount_ml": c.amount_ml,
        "diaper_type": (
            c.diaper_type.value if hasattr(c.diaper_type, "value") else c.diaper_type
        )
        if c.diaper_type is not None
        else None,
        "note": c.note,
        "created_at": _iso(c.created_at),
    }


def _reminder_dict(r: Reminder) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "kind": r.kind.value if hasattr(r.kind, "value") else r.kind,
        "due_at": _iso(r.due_at),
        "completed_at": _iso(r.completed_at),
        "note": r.note,
        "created_at": _iso(r.created_at),
    }


@router.get(
    "",
    summary="Premium: bebek verisini ZIP olarak indir",
    responses={200: {"content": {"application/zip": {}}}},
)
def export_baby(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Response:
    baby = _ensure_owned_baby(db, current_user.id, baby_id)

    if not is_premium(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Bulut yedek Premium pakette yer alır. "
                "Tüm verilerini ZIP olarak indirmek için Premium'a geç."
            ),
        )

    albums = list(db.execute(select(Album).where(Album.baby_id == baby_id)).scalars())
    entries = list(
        db.execute(
            select(JournalEntry).where(JournalEntry.baby_id == baby_id)
        ).scalars()
    )
    milestones = list(
        db.execute(select(Milestone).where(Milestone.baby_id == baby_id)).scalars()
    )
    care_logs = list(
        db.execute(select(CareLog).where(CareLog.baby_id == baby_id)).scalars()
    )
    reminders = list(
        db.execute(select(Reminder).where(Reminder.baby_id == baby_id)).scalars()
    )

    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "baby": _baby_dict(baby),
        "albums": [_album_dict(a) for a in albums],
        "journal_entries": [_entry_dict(e) for e in entries],
        "milestones": [_milestone_dict(m) for m in milestones],
        "care_logs": [_care_log_dict(c) for c in care_logs],
        "reminders": [_reminder_dict(r) for r in reminders],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "manifest.json",
            json.dumps(manifest, indent=2, ensure_ascii=False),
        )
        # Tüm medyayı MinIO'dan çek ve "media/" altına ekle
        for entry in entries:
            for m in entry.media:
                data = storage.download_bytes(m.object_key)
                if not data:
                    continue
                # ZIP içindeki path: media/<object_key>
                zf.writestr(f"media/{m.object_key}", data)

    buf.seek(0)
    safe_name = "".join(ch for ch in baby.name if ch.isalnum() or ch in "-_") or "baby"
    filename = f"beberehber-{safe_name}-{baby_id}.zip"

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
