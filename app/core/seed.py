"""Demo seed — idempotent. Docker compose up sırasında çalışır (cli.py)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.album import Album
from app.models.baby import Baby, BabyGender
from app.models.baby_member import BabyMember, BabyMemberRole
from app.models.care_log import CareKind, CareLog, DiaperType
from app.models.community_post import CommunityCategory, CommunityPost
from app.models.journal_entry import JournalEntry
from app.models.milestone import Milestone, MilestoneCategory
from app.models.reminder import Reminder, ReminderKind
from app.models.social_post import SocialPlatform, SocialPost, SocialPostStatus
from app.models.user import User, UserPlan, UserRole


DEMO_PASSWORD = "demo1234"

DEMO_USERS: list[dict[str, object]] = [
    {
        "email": "deniz@example.com",
        "name": "Deniz",
        "plan": UserPlan.PREMIUM,
        "role": UserRole.USER,
    },
    {
        "email": "free@example.com",
        "name": "Ücretsiz Kullanıcı",
        "plan": UserPlan.FREE,
        "role": UserRole.USER,
    },
    {
        "email": "admin@example.com",
        "name": "Yönetici",
        "plan": UserPlan.PREMIUM,
        "role": UserRole.ADMIN,
    },
]


def seed_demo_users(db: Session) -> int:
    """Idempotently insert demo users. Returns number of newly created rows."""
    created = 0
    password_hash = hash_password(DEMO_PASSWORD)

    for entry in DEMO_USERS:
        email = str(entry["email"])
        existing = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing is not None:
            continue

        user = User(
            email=email,
            name=str(entry["name"]),
            password_hash=password_hash,
            plan=entry["plan"],  # type: ignore[arg-type]
            role=entry["role"],  # type: ignore[arg-type]
        )
        db.add(user)
        created += 1

    if created:
        db.commit()
    return created


# ---------------------------------------------------------------------------


def _get_user(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def seed_demo_data(db: Session) -> dict[str, int]:
    """Premium kullanıcı için bebek + 7 günlük bakım + milestone + hatırlatıcı,
    admin için topluluk + sosyal medya içerikleri ekler. Idempotent.

    Returns: oluşturulan kayıt sayıları (her tablo için).
    """
    stats: dict[str, int] = {
        "babies": 0,
        "care_logs": 0,
        "milestones": 0,
        "reminders": 0,
        "albums": 0,
        "journal_entries": 0,
        "community_posts": 0,
        "social_posts": 0,
    }

    deniz = _get_user(db, "deniz@example.com")
    admin = _get_user(db, "admin@example.com")

    if deniz is not None:
        baby, created_baby = _ensure_deniz_baby(db, deniz)
        if baby is not None:
            if created_baby:
                stats["babies"] = 1
            stats["care_logs"] = _ensure_care_logs(db, baby)
            stats["milestones"] = _ensure_milestones(db, baby)
            stats["reminders"] = _ensure_reminders(db, baby)
            album_n, entry_n = _ensure_journal(db, baby)
            stats["albums"] = album_n
            stats["journal_entries"] = entry_n

    if admin is not None:
        stats["community_posts"] = _ensure_community_posts(db, admin)
        stats["social_posts"] = _ensure_social_posts(db, admin)

    return stats


# --------------------------- Baby ---------------------------


def _ensure_deniz_baby(db: Session, deniz: User) -> tuple[Baby | None, bool]:
    existing = db.execute(
        select(Baby).where(Baby.owner_id == deniz.id, Baby.name == "Ada")
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    baby = Baby(
        owner_id=deniz.id,
        name="Ada",
        birth_date=date(2025, 8, 15),
        gender=BabyGender.GIRL,
    )
    db.add(baby)
    db.flush()
    db.add(
        BabyMember(
            baby_id=baby.id,
            user_id=deniz.id,
            role=BabyMemberRole.OWNER,
        )
    )
    db.commit()
    return baby, True


# --------------------------- Care logs ---------------------------


def _ensure_care_logs(db: Session, baby: Baby) -> int:
    existing = db.scalar(select(CareLog).where(CareLog.baby_id == baby.id).limit(1))
    if existing is not None:
        return 0

    today = _today()
    rows: list[CareLog] = []

    for d in range(7):
        day = today - timedelta(days=d)
        y, m, dd = day.year, day.month, day.day

        # Gece uykusu (önceki günden 22:00 → bugün 06:30)
        prev = day - timedelta(days=1)
        rows.append(
            CareLog(
                baby_id=baby.id,
                kind=CareKind.SLEEP,
                started_at=_utc(prev.year, prev.month, prev.day, 22, 0),
                ended_at=_utc(y, m, dd, 6, 30),
                note="Gece uykusu",
            )
        )
        # Öğle şekerlemesi
        rows.append(
            CareLog(
                baby_id=baby.id,
                kind=CareKind.SLEEP,
                started_at=_utc(y, m, dd, 13, 0),
                ended_at=_utc(y, m, dd, 14, 45),
                note="Öğle şekerlemesi",
            )
        )
        # 4 besleme
        for hour, ml in ((8, 120), (12, 150), (16, 120), (20, 180)):
            rows.append(
                CareLog(
                    baby_id=baby.id,
                    kind=CareKind.FEEDING,
                    started_at=_utc(y, m, dd, hour, 0),
                    amount_ml=ml,
                )
            )
        # 4 bez
        for hour, dt in (
            (8, DiaperType.PEE),
            (13, DiaperType.BOTH),
            (17, DiaperType.PEE),
            (21, DiaperType.POOP),
        ):
            rows.append(
                CareLog(
                    baby_id=baby.id,
                    kind=CareKind.DIAPER,
                    started_at=_utc(y, m, dd, hour, 15),
                    diaper_type=dt,
                )
            )

    db.add_all(rows)
    db.commit()
    return len(rows)


# --------------------------- Milestones ---------------------------


def _ensure_milestones(db: Session, baby: Baby) -> int:
    existing = db.scalar(select(Milestone).where(Milestone.baby_id == baby.id).limit(1))
    if existing is not None:
        return 0

    items = [
        (
            "first_smile",
            "İlk sosyal gülümseme",
            MilestoneCategory.SOCIAL,
            date(2025, 10, 20),
        ),
        (
            "head_control",
            "Başını dik tutar",
            MilestoneCategory.MOTOR,
            date(2025, 11, 15),
        ),
        (
            "rolls_over",
            "Yuvarlanır (sırt → karın)",
            MilestoneCategory.MOTOR,
            date(2025, 12, 18),
        ),
        (
            "babbles",
            "Babıldar (ba-ba, ma-ma)",
            MilestoneCategory.LANGUAGE,
            date(2026, 2, 5),
        ),
        (
            "sits_unsupported",
            "Desteksiz oturur",
            MilestoneCategory.MOTOR,
            date(2026, 2, 28),
        ),
        (None, "Köpeğe el salladı", MilestoneCategory.OTHER, date(2026, 4, 12)),
    ]
    rows = [
        Milestone(
            baby_id=baby.id,
            preset_id=preset_id,
            title=title,
            category=cat,
            reached_on=reached,
        )
        for (preset_id, title, cat, reached) in items
    ]
    db.add_all(rows)
    db.commit()
    return len(rows)


# --------------------------- Reminders ---------------------------


def _ensure_reminders(db: Session, baby: Baby) -> int:
    existing = db.scalar(select(Reminder).where(Reminder.baby_id == baby.id).limit(1))
    if existing is not None:
        return 0

    today = _today()
    rows = [
        Reminder(
            baby_id=baby.id,
            title="9. ay kontrolü",
            kind=ReminderKind.APPOINTMENT,
            due_at=datetime.combine(
                today + timedelta(days=5), datetime.min.time(), tzinfo=timezone.utc
            ).replace(hour=10, minute=30),
            note="Pediatri kontrolü",
        ),
        Reminder(
            baby_id=baby.id,
            title="12. ay aşıları",
            kind=ReminderKind.VACCINE,
            due_at=datetime.combine(
                today + timedelta(days=14), datetime.min.time(), tzinfo=timezone.utc
            ).replace(hour=9, minute=0),
        ),
        Reminder(
            baby_id=baby.id,
            title="Aile fotoğrafı",
            kind=ReminderKind.GENERAL,
            due_at=datetime.combine(
                today + timedelta(days=20), datetime.min.time(), tzinfo=timezone.utc
            ).replace(hour=14, minute=0),
            note="Doğal ışıkta park",
        ),
    ]
    db.add_all(rows)
    db.commit()
    return len(rows)


# --------------------------- Journal ---------------------------


def _ensure_journal(db: Session, baby: Baby) -> tuple[int, int]:
    existing = db.scalar(select(Album).where(Album.baby_id == baby.id).limit(1))
    if existing is not None:
        return (0, 0)

    album = Album(baby_id=baby.id, name="İlk yıl")
    db.add(album)
    db.flush()

    entries = [
        JournalEntry(
            baby_id=baby.id,
            album_id=album.id,
            title="İlk gülümseme",
            body="Sabah uyandığında bana baktı ve geniş bir gülümseme verdi.",
            occurred_on=date(2025, 10, 20),
        ),
        JournalEntry(
            baby_id=baby.id,
            album_id=album.id,
            title="Sahil günü",
            body="İlk kez denizi gördü; kuma dokunmaya çekindi ama sonra çok eğlendi.",
            occurred_on=date(2026, 5, 1),
        ),
    ]
    db.add_all(entries)
    db.commit()
    return (1, len(entries))


# --------------------------- Community ---------------------------


def _ensure_community_posts(db: Session, admin: User) -> int:
    existing = db.scalar(
        select(CommunityPost).where(CommunityPost.is_expert.is_(True)).limit(1)
    )
    if existing is not None:
        return 0

    items = [
        (
            "Pediatristten 0-12 ay aşı takvimi",
            "Hep sorulan aşı zamanlamaları ve pratik bilgiler. Hatırlatıcı kurmak "
            "için BebeRehber'in hatırlatıcı modülünü kullanmanı öneririm.",
            CommunityCategory.HEALTH,
        ),
        (
            "Bebek uykusu için sabit rutin önerisi",
            "Sürdürülebilir bir uyku düzeni için akşam saatlerinde sabit ışık + "
            "ortam sıcaklığı 21-22°C + son besleme saati en kritik üç değişken.",
            CommunityCategory.SLEEP,
        ),
    ]
    rows = [
        CommunityPost(
            author_id=admin.id,
            title=title,
            body=body,
            category=cat,
            is_expert=True,
        )
        for (title, body, cat) in items
    ]
    db.add_all(rows)
    db.commit()
    return len(rows)


# --------------------------- Social ---------------------------


def _ensure_social_posts(db: Session, admin: User) -> int:
    existing = db.scalar(select(SocialPost).limit(1))
    if existing is not None:
        return 0

    now = datetime.now(timezone.utc)
    rows = [
        SocialPost(
            author_id=admin.id,
            platform=SocialPlatform.INSTAGRAM,
            title="Lansman duyurusu — BebeRehber yayında!",
            body="Ebeveynliğin dijital rehberi BebeRehber artık yayında.",
            status=SocialPostStatus.PUBLISHED,
            scheduled_for=now - timedelta(days=10),
            published_at=now - timedelta(days=10),
            likes=156,
            comments_count=24,
            shares=18,
            reach=12_400,
        ),
        SocialPost(
            author_id=admin.id,
            platform=SocialPlatform.TIKTOK,
            title="Story: uyku takibi nasıl çalışır",
            body="30 saniyelik kısa video — uyku başla/bitir butonları + 7 günlük grafik.",
            status=SocialPostStatus.SCHEDULED,
            scheduled_for=now + timedelta(days=3),
        ),
        SocialPost(
            author_id=admin.id,
            platform=SocialPlatform.X,
            title="Aile paylaşımı duyurusu",
            body="Premium kullanıcılar artık bebek profilini eşiyle paylaşabiliyor.",
            status=SocialPostStatus.DRAFT,
        ),
    ]
    db.add_all(rows)
    db.commit()
    return len(rows)
