"""Demo seed — idempotent. Docker compose up sırasında çalışır (cli.py)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.album import Album
from app.models.baby import Baby, BabyGender
from app.models.baby_member import BabyMember, BabyMemberRole, BabyRelationship
from app.models.care_log import CareKind, CareLog, DiaperType
from app.models.community_comment import CommunityComment
from app.models.community_post import CommunityCategory, CommunityPost
from app.models.guide_article import GuideArticle, GuideCategory
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
        # Free hesap — Deniz'in (Premium owner) davet edeceği co-parent.
        # Davet kabul edince Premium gate'leri Ada üzerinden açılır.
        "email": "mehmet@example.com",
        "name": "Mehmet Yılmaz",
        "plan": UserPlan.FREE,
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


def _set_owner_relationship(
    db: Session, baby_id: int, user_id: int, rel: BabyRelationship
) -> None:
    """Mevcut owner BabyMember'a relationship ata (idempotent)."""
    member = db.scalar(
        select(BabyMember).where(
            BabyMember.baby_id == baby_id,
            BabyMember.user_id == user_id,
        )
    )
    if member is None or member.relationship is not None:
        return
    member.relationship = rel
    db.commit()


def _ensure_co_parent(
    db: Session, baby_id: int, user_id: int, rel: BabyRelationship
) -> None:
    """Co-parent BabyMember yoksa ekle, relationship belirle (idempotent)."""
    existing = db.scalar(
        select(BabyMember).where(
            BabyMember.baby_id == baby_id,
            BabyMember.user_id == user_id,
        )
    )
    if existing is not None:
        if existing.relationship is None:
            existing.relationship = rel
            db.commit()
        return
    db.add(
        BabyMember(
            baby_id=baby_id,
            user_id=user_id,
            role=BabyMemberRole.CO_PARENT,
            relationship=rel,
        )
    )
    db.commit()


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
        "guide_articles": 0,
    }

    deniz = _get_user(db, "deniz@example.com")
    admin = _get_user(db, "admin@example.com")
    mehmet = _get_user(db, "mehmet@example.com")

    if deniz is not None:
        baby, created_baby = _ensure_deniz_baby(db, deniz)
        if baby is not None:
            if created_baby:
                stats["babies"] += 1
            # Owner relationship = ANNE (Deniz)
            _set_owner_relationship(db, baby.id, deniz.id, BabyRelationship.MOTHER)
            stats["care_logs"] += _ensure_care_logs(db, baby, author_id=deniz.id)
            stats["milestones"] += _ensure_milestones(db, baby, author_id=deniz.id)
            stats["reminders"] += _ensure_reminders(db, baby, author_id=deniz.id)
            album_n, entry_n = _ensure_journal(db, baby, author_id=deniz.id)
            stats["albums"] += album_n
            stats["journal_entries"] += entry_n

            # Mehmet'i Ada'ya BABA olarak co-parent ekle (demo)
            if mehmet is not None:
                _ensure_co_parent(db, baby.id, mehmet.id, BabyRelationship.FATHER)

        # İkinci bebek: Cem (yenidoğan, ~2 aylık) — BabySwitcher + farklı yaş
        cem, created_cem = _ensure_deniz_baby_cem(db, deniz)
        if cem is not None:
            if created_cem:
                stats["babies"] += 1
            _set_owner_relationship(db, cem.id, deniz.id, BabyRelationship.MOTHER)
            stats["care_logs"] += _ensure_newborn_care_logs(db, cem, author_id=deniz.id)
            stats["milestones"] += _ensure_newborn_milestones(
                db, cem, author_id=deniz.id
            )
            stats["reminders"] += _ensure_newborn_reminders(db, cem, author_id=deniz.id)
            if mehmet is not None:
                _ensure_co_parent(db, cem.id, mehmet.id, BabyRelationship.FATHER)

    if admin is not None:
        stats["community_posts"] = _ensure_community_posts(db, admin)
        stats["social_posts"] = _ensure_social_posts(db, admin)
        stats["guide_articles"] = _ensure_guide_articles(db, admin)

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


def _ensure_deniz_baby_cem(db: Session, deniz: User) -> tuple[Baby | None, bool]:
    """İkinci bebek: Cem (~2 aylık yenidoğan).

    BabySwitcher demo'su + farklı yaş aralığı için kişiselleştirilmiş öneri
    motorunun farklı çıktılar üretebilmesi için.
    """
    existing = db.execute(
        select(Baby).where(Baby.owner_id == deniz.id, Baby.name == "Cem")
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    # Bugünden 60 gün önce — testler "fixed today" ile etkilenmesin diye
    # build sırasındaki gerçek tarihi kullanıyoruz (seed cli ile çalışıyor).
    birth = _today() - timedelta(days=60)
    baby = Baby(
        owner_id=deniz.id,
        name="Cem",
        birth_date=birth,
        gender=BabyGender.BOY,
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


def _ensure_newborn_care_logs(
    db: Session, baby: Baby, author_id: int | None = None
) -> int:
    """Yenidoğan pattern (Cem için): son 7 gün, sık besleme + uzun uyku."""
    existing = db.scalar(select(CareLog).where(CareLog.baby_id == baby.id).limit(1))
    if existing is not None:
        return 0

    today = _today()
    rows: list[CareLog] = []

    for d in range(7):
        day = today - timedelta(days=d)
        y, m, dd = day.year, day.month, day.day
        prev = day - timedelta(days=1)

        # Gece uyandırıldığı için bölük uyku
        rows.append(
            CareLog(
                baby_id=baby.id,
                kind=CareKind.SLEEP,
                started_at=_utc(prev.year, prev.month, prev.day, 22, 0),
                ended_at=_utc(y, m, dd, 2, 30),
                note="Gece I",
            )
        )
        rows.append(
            CareLog(
                baby_id=baby.id,
                kind=CareKind.SLEEP,
                started_at=_utc(y, m, dd, 3, 30),
                ended_at=_utc(y, m, dd, 7, 0),
                note="Gece II",
            )
        )
        # Gün içi 3 şekerleme
        for start_h, end_h in ((9, 11), (13, 15), (17, 18)):
            rows.append(
                CareLog(
                    baby_id=baby.id,
                    kind=CareKind.SLEEP,
                    started_at=_utc(y, m, dd, start_h, 0),
                    ended_at=_utc(y, m, dd, end_h, 0),
                )
            )
        # 7-8 besleme (yenidoğan: 2-3 saatte bir)
        for hour, ml in (
            (3, 90),
            (6, 100),
            (9, 110),
            (12, 110),
            (15, 100),
            (18, 110),
            (21, 120),
        ):
            rows.append(
                CareLog(
                    baby_id=baby.id,
                    kind=CareKind.FEEDING,
                    started_at=_utc(y, m, dd, hour, 0),
                    amount_ml=ml,
                )
            )
        # 6 bez
        for hour, dt in (
            (7, DiaperType.PEE),
            (10, DiaperType.POOP),
            (13, DiaperType.PEE),
            (16, DiaperType.BOTH),
            (19, DiaperType.PEE),
            (22, DiaperType.PEE),
        ):
            rows.append(
                CareLog(
                    baby_id=baby.id,
                    kind=CareKind.DIAPER,
                    started_at=_utc(y, m, dd, hour, 30),
                    diaper_type=dt,
                )
            )

    if author_id is not None:
        for r in rows:
            r.created_by_user_id = author_id
    db.add_all(rows)
    db.commit()
    return len(rows)


def _ensure_newborn_milestones(
    db: Session, baby: Baby, author_id: int | None = None
) -> int:
    """Cem için 1-2 yaşa uygun milestone (sosyal gülümseme, baş tutma erken)."""
    existing = db.scalar(select(Milestone).where(Milestone.baby_id == baby.id).limit(1))
    if existing is not None:
        return 0

    today = _today()
    rows = [
        Milestone(
            baby_id=baby.id,
            preset_id="social_smile",
            title="İlk sosyal gülümseme",
            category=MilestoneCategory.SOCIAL,
            reached_on=today - timedelta(days=15),
        ),
        Milestone(
            baby_id=baby.id,
            preset_id=None,
            title="Sesini duyunca dönüyor",
            category=MilestoneCategory.SOCIAL,
            reached_on=today - timedelta(days=4),
        ),
    ]
    if author_id is not None:
        for r in rows:
            r.created_by_user_id = author_id
    db.add_all(rows)
    db.commit()
    return len(rows)


def _ensure_newborn_reminders(
    db: Session, baby: Baby, author_id: int | None = None
) -> int:
    existing = db.scalar(select(Reminder).where(Reminder.baby_id == baby.id).limit(1))
    if existing is not None:
        return 0

    today = _today()

    def _at(offset_days: int, hour: int, minute: int = 0) -> datetime:
        return datetime.combine(
            today + timedelta(days=offset_days),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).replace(hour=hour, minute=minute)

    rows = [
        Reminder(
            baby_id=baby.id,
            title="1. ay kontrolü",
            kind=ReminderKind.APPOINTMENT,
            due_at=_at(-30, 11, 0),
            completed_at=_at(-30, 12, 30),
            note="Sağlıklı — kilo +800g",
        ),
        Reminder(
            baby_id=baby.id,
            title="2. ay aşıları (Hep B + DBT)",
            kind=ReminderKind.VACCINE,
            due_at=_at(3, 9, 30),
        ),
        Reminder(
            baby_id=baby.id,
            title="Göbek bandı kontrolü",
            kind=ReminderKind.GENERAL,
            due_at=_at(1, 8, 0),
            note="Kuru ve temiz kaldı mı?",
        ),
    ]
    if author_id is not None:
        for r in rows:
            r.created_by_user_id = author_id
    db.add_all(rows)
    db.commit()
    return len(rows)


# --------------------------- Care logs ---------------------------


def _ensure_care_logs(db: Session, baby: Baby, author_id: int | None = None) -> int:
    """Ada için 30 günlük gerçekçi bakım pattern'i (uyku/besleme/bez).

    Her gün küçük varyasyonlarla; Premium 30 günlük analiz seçeneği zengin
    görünür, kişiselleştirilmiş öneri motoru anlamlı sinyal üretir.
    """
    existing = db.scalar(select(CareLog).where(CareLog.baby_id == baby.id).limit(1))
    if existing is not None:
        return 0

    today = _today()
    rows: list[CareLog] = []

    # Tekrarlanabilir varyasyon — index'e göre küçük dalgalanmalar
    def _wobble(base: int, mod: int, amp: int) -> int:
        return base + ((mod * 7) % (amp * 2 + 1)) - amp

    for d in range(30):
        day = today - timedelta(days=d)
        y, m, dd = day.year, day.month, day.day
        prev = day - timedelta(days=1)

        # Gece uykusu — bitiş ±20 dk dalgalı (06:10–06:50 arası)
        end_min = 30 + _wobble(0, d, 20)
        rows.append(
            CareLog(
                baby_id=baby.id,
                kind=CareKind.SLEEP,
                started_at=_utc(prev.year, prev.month, prev.day, 22, 0),
                ended_at=_utc(y, m, dd, 6, max(0, min(59, end_min))),
                note="Gece uykusu",
            )
        )
        # Öğle şekerlemesi — süre 90–120 dk
        nap_end = 45 + _wobble(0, d + 3, 15)
        rows.append(
            CareLog(
                baby_id=baby.id,
                kind=CareKind.SLEEP,
                started_at=_utc(y, m, dd, 13, 0),
                ended_at=_utc(y, m, dd, 14, max(0, min(59, nap_end))),
                note="Öğle şekerlemesi",
            )
        )
        # Bazı günler kısa bir akşamüstü şekerlemesi de var
        if d % 3 == 0:
            rows.append(
                CareLog(
                    baby_id=baby.id,
                    kind=CareKind.SLEEP,
                    started_at=_utc(y, m, dd, 17, 30),
                    ended_at=_utc(y, m, dd, 18, 10),
                    note="Akşamüstü kestirme",
                )
            )

        # 4 besleme, miktar ±20ml dalgalı (dakika sabit, sadece ml wobble)
        feedings = ((8, 120), (12, 150), (16, 120), (20, 180))
        for i, (hour, ml) in enumerate(feedings):
            rows.append(
                CareLog(
                    baby_id=baby.id,
                    kind=CareKind.FEEDING,
                    started_at=_utc(y, m, dd, hour, 0),
                    amount_ml=ml + _wobble(0, d * 2 + i, 20),
                )
            )
        # Bazı günler 5. besleme (gece arası)
        if d % 4 == 0:
            rows.append(
                CareLog(
                    baby_id=baby.id,
                    kind=CareKind.FEEDING,
                    started_at=_utc(y, m, dd, 2, 30),
                    amount_ml=140,
                    note="Gece beslemesi",
                )
            )

        # 4 bez, son haftada 5 (yaşa uygun küçük artış)
        diapers = [
            (8, DiaperType.PEE),
            (13, DiaperType.BOTH),
            (17, DiaperType.PEE),
            (21, DiaperType.POOP),
        ]
        if d < 7:
            diapers.append((11, DiaperType.PEE))
        for hour, dt in diapers:
            rows.append(
                CareLog(
                    baby_id=baby.id,
                    kind=CareKind.DIAPER,
                    started_at=_utc(y, m, dd, hour, 15),
                    diaper_type=dt,
                )
            )

    if author_id is not None:
        for r in rows:
            r.created_by_user_id = author_id
    db.add_all(rows)
    db.commit()
    return len(rows)


# --------------------------- Milestones ---------------------------


def _ensure_milestones(db: Session, baby: Baby, author_id: int | None = None) -> int:
    existing = db.scalar(select(Milestone).where(Milestone.baby_id == baby.id).limit(1))
    if existing is not None:
        return 0

    items = [
        (
            "social_smile",
            "İlk sosyal gülümseme",
            MilestoneCategory.SOCIAL,
            date(2025, 10, 20),
        ),
        (
            None,
            "Yüksek sesli kahkaha",
            MilestoneCategory.SOCIAL,
            date(2025, 11, 8),
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
            None,
            "İlk ek gıda — havuç püresi",
            MilestoneCategory.PHYSICAL,
            date(2026, 1, 22),
        ),
        (
            "babbles",
            "Babıldar (ba-ba, ma-ma)",
            MilestoneCategory.LANGUAGE,
            date(2026, 2, 5),
        ),
        (
            "sits_supported",
            "Desteksiz oturur",
            MilestoneCategory.MOTOR,
            date(2026, 2, 28),
        ),
        (
            None,
            "İlk diş çıktı (alt ön)",
            MilestoneCategory.PHYSICAL,
            date(2026, 3, 14),
        ),
        (
            None,
            "Adını duyunca dönüyor",
            MilestoneCategory.LANGUAGE,
            date(2026, 4, 2),
        ),
        (None, "Köpeğe el salladı", MilestoneCategory.SOCIAL, date(2026, 4, 12)),
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
    if author_id is not None:
        for r in rows:
            r.created_by_user_id = author_id
    db.add_all(rows)
    db.commit()
    return len(rows)


# --------------------------- Reminders ---------------------------


def _ensure_reminders(db: Session, baby: Baby, author_id: int | None = None) -> int:
    existing = db.scalar(select(Reminder).where(Reminder.baby_id == baby.id).limit(1))
    if existing is not None:
        return 0

    today = _today()

    def _at(offset_days: int, hour: int, minute: int = 0) -> datetime:
        return datetime.combine(
            today + timedelta(days=offset_days),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).replace(hour=hour, minute=minute)

    rows = [
        # Geçmişte tamamlanmış — geçmiş referansı + Aile/Premium history için
        Reminder(
            baby_id=baby.id,
            title="6. ay kontrolü",
            kind=ReminderKind.APPOINTMENT,
            due_at=_at(-45, 10, 0),
            completed_at=_at(-45, 11, 30),
            note="Pediatri rutin kontrolü — tamamlandı",
        ),
        Reminder(
            baby_id=baby.id,
            title="D vitamini takviyesi (haftalık)",
            kind=ReminderKind.GENERAL,
            due_at=_at(-3, 9, 0),
            completed_at=_at(-3, 9, 15),
        ),
        # Yaklaşan — bugünden sonra
        Reminder(
            baby_id=baby.id,
            title="9. ay kontrolü",
            kind=ReminderKind.APPOINTMENT,
            due_at=_at(5, 10, 30),
            note="Pediatri kontrolü",
        ),
        Reminder(
            baby_id=baby.id,
            title="Demir takviyesi başlangıç",
            kind=ReminderKind.GENERAL,
            due_at=_at(2, 8, 30),
            note="6 ay sonrası rutin",
        ),
        Reminder(
            baby_id=baby.id,
            title="12. ay aşıları",
            kind=ReminderKind.VACCINE,
            due_at=_at(14, 9, 0),
        ),
        Reminder(
            baby_id=baby.id,
            title="Aile fotoğrafı çekimi",
            kind=ReminderKind.GENERAL,
            due_at=_at(20, 14, 0),
            note="Doğal ışıkta park — sage ton ağırlıklı kıyafet",
        ),
    ]
    if author_id is not None:
        for r in rows:
            r.created_by_user_id = author_id
    db.add_all(rows)
    db.commit()
    return len(rows)


# --------------------------- Journal ---------------------------


def _ensure_journal(
    db: Session, baby: Baby, author_id: int | None = None
) -> tuple[int, int]:
    existing = db.scalar(select(Album).where(Album.baby_id == baby.id).limit(1))
    if existing is not None:
        return (0, 0)

    album_ilk_yil = Album(baby_id=baby.id, name="İlk yıl")
    album_aile = Album(baby_id=baby.id, name="Aile anları")
    album_gezi = Album(baby_id=baby.id, name="Gezi ve doğa")
    db.add_all([album_ilk_yil, album_aile, album_gezi])
    db.flush()

    entries = [
        JournalEntry(
            baby_id=baby.id,
            album_id=album_ilk_yil.id,
            title="İlk gülümseme",
            body="Sabah uyandığında bana baktı ve geniş bir gülümseme verdi.",
            occurred_on=date(2025, 10, 20),
        ),
        JournalEntry(
            baby_id=baby.id,
            album_id=album_aile.id,
            title="Anneanne ile ilk tanışma",
            body=(
                "Anneanne kapıdan girer girmez bütün gözleri ona kilitlendi. "
                "Kucağına alınca uzun süre ağladığı bir öğleden sonra geçti."
            ),
            occurred_on=date(2025, 11, 30),
        ),
        JournalEntry(
            baby_id=baby.id,
            album_id=album_ilk_yil.id,
            title="İlk ek gıda — havuç püresi",
            body=(
                "Kaşığı uzattığımda yüzünü buruşturdu ama ikinci kaşıkta kabul "
                "etti. Üzerinde kalan turuncu izleri silmek zor oldu."
            ),
            occurred_on=date(2026, 1, 22),
        ),
        JournalEntry(
            baby_id=baby.id,
            album_id=album_gezi.id,
            title="Park gezisi",
            body="Yapraklara dokunmayı çok sevdi. Salıncak ilk başta korkuttu.",
            occurred_on=date(2026, 3, 5),
        ),
        JournalEntry(
            baby_id=baby.id,
            album_id=album_aile.id,
            title="6 aylık fotoğraf çekimi",
            body=(
                "Sage tonunda kıyafet + doğal ışık. Profesyonel olmayan ama "
                "ailenin en sevdiği seri oldu."
            ),
            occurred_on=date(2026, 2, 14),
        ),
        JournalEntry(
            baby_id=baby.id,
            album_id=album_gezi.id,
            title="Sahil günü",
            body="İlk kez denizi gördü; kuma dokunmaya çekindi ama sonra çok eğlendi.",
            occurred_on=date(2026, 5, 1),
        ),
    ]
    if author_id is not None:
        for a in (album_ilk_yil, album_aile, album_gezi):
            a.created_by_user_id = author_id
        for e in entries:
            e.created_by_user_id = author_id
    db.add_all(entries)
    db.commit()
    return (3, len(entries))


# --------------------------- Community ---------------------------


def _ensure_community_posts(db: Session, admin: User) -> int:
    """Uzman post'ları + Deniz'den 3 ebeveyn paylaşımı + birkaç yorum.

    Topluluk modülünü "boş" göstermemek için. Filtre chip'leri, uzman rozeti,
    yorum listesi ve farklı kategoriler için yeterli demo verisi.
    """
    existing = db.scalar(
        select(CommunityPost).where(CommunityPost.is_expert.is_(True)).limit(1)
    )
    if existing is not None:
        return 0

    # Uzman post'ları (admin yazdı, is_expert=True)
    expert_items: list[tuple[str, str, CommunityCategory]] = [
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
        (
            "6 ay sonrası ek gıda — ne ile başlamalı?",
            "Tek gıdalı, az miktarda başla. Önce sebze püresi, sonra meyve, sonra "
            "et ve tahıllar. Yeni bir gıda eklediğinde 3 gün ara ver ki alerji "
            "varsa fark edesin. Bal 1 yaş öncesi yasak.",
            CommunityCategory.FEEDING,
        ),
    ]
    expert_posts = [
        CommunityPost(
            author_id=admin.id,
            title=title,
            body=body,
            category=cat,
            is_expert=True,
        )
        for (title, body, cat) in expert_items
    ]
    db.add_all(expert_posts)
    db.flush()

    # Ebeveyn paylaşımları (Deniz yazdı, is_expert=False)
    deniz = _get_user(db, "deniz@example.com")
    parent_posts: list[CommunityPost] = []
    if deniz is not None:
        parent_items: list[tuple[str, str, CommunityCategory]] = [
            (
                "İlk diş çıkarken huysuzlandı — ne işe yaradı?",
                "Ada 7 aylıkken alt ön diş çıkarırken 3 gün boyunca çok ağladı. "
                "Soğuk diş halkası + bol kucak işe yaradı. Sizde işe yarayan "
                "başka pratikler var mı?",
                CommunityCategory.DEVELOPMENT,
            ),
            (
                "Anneanneye bebek bırakmak — ilk ayrılık",
                "İlk kez 4 saat dışarıda kaldım, döndüğümde Ada gayet iyiydi ama "
                "ben fena halde özlemiştim :) Sizin ilk ayrılığınız nasıldı?",
                CommunityCategory.GENERAL,
            ),
            (
                "Gece uyandırılan beslemeyi nasıl bıraktınız?",
                "Ada 6 ay+, hâlâ gece 3'te uyanıp beslenmek istiyor. Yavaş yavaş "
                "azaltmak istiyorum ama 'aniden mi tedrici mi' kararsızım. "
                "Deneyimleri duymak isterim.",
                CommunityCategory.SLEEP,
            ),
        ]
        parent_posts = [
            CommunityPost(
                author_id=deniz.id,
                title=title,
                body=body,
                category=cat,
                is_expert=False,
            )
            for (title, body, cat) in parent_items
        ]
        db.add_all(parent_posts)
        db.flush()

    # İlk uzman post'a iki yorum
    if expert_posts:
        first = expert_posts[0]
        comments: list[CommunityComment] = []
        if deniz is not None:
            comments.append(
                CommunityComment(
                    post_id=first.id,
                    author_id=deniz.id,
                    body="Teşekkürler, 9. ay aşılarını hatırlatıcıya hemen aldım.",
                )
            )
        comments.append(
            CommunityComment(
                post_id=first.id,
                author_id=admin.id,
                body="Aşı sonrası ateş yüksekse 1-2 gün izleyip pediatristine danışman yeterli.",
            )
        )
        if comments:
            db.add_all(comments)

    db.commit()
    return len(expert_posts) + len(parent_posts)


# --------------------------- Guide articles ---------------------------


def _ensure_guide_articles(db: Session, admin: User) -> int:
    existing = db.scalar(select(GuideArticle).limit(1))
    if existing is not None:
        return 0

    items: list[tuple[str, str, str, str, GuideCategory]] = [
        (
            "hamilelikte-ilk-3-ay",
            "Hamilelikte ilk 3 ay: değişimler ve dikkat edilecekler",
            "Bulantı, yorgunluk ve duygusal dalgalanmalar normaldir. "
            "İlk trimestrde takip etmen gereken temel başlıklar.",
            "Hamileliğin ilk üç ayında vücudun hızla değişir: hormon dalgalanmaları, "
            "bulantı (özellikle sabah), yorgunluk ve memelerde hassasiyet en sık "
            "yaşanan değişimlerdir.\n\n"
            "**İlk doktor randevusu** 6-8. hafta arası önerilir. "
            "Folik asit takviyesi (günde 400-800 mcg) ve B12 takibi bu dönemde "
            "kritiktir.\n\n"
            "Çiğ et, çiğ balık, pastörize edilmemiş süt ürünleri ve fazla kafeinden "
            "uzak dur. Su tüketimine dikkat et — günde 2-2.5 litre hedef.",
            GuideCategory.PREGNANCY,
        ),
        (
            "yenidogan-bakimi-0-3-ay",
            "Yenidoğan bakımı: 0-3 ay temel rehber",
            "Beslenme, uyku düzeni, göbek bakımı ve ilk doktor kontrolleri için "
            "yenidoğan dönemi rehberi.",
            "Yenidoğan dönemi (0-3 ay) bebeğin dünyaya uyum sağladığı dönemdir.\n\n"
            "**Beslenme:** 2-3 saatte bir, günde 8-12 kez. Anne sütü ilk 6 ay "
            "tek başına yeterlidir.\n\n"
            "**Uyku:** Günde toplam 14-17 saat, ama parça parça. Sırtüstü "
            "yatırılması SIDS riskini azaltır.\n\n"
            "**Göbek bakımı:** Düşene kadar (genellikle 1-3 hafta) temiz ve kuru "
            "tutulmalı. Alkol veya antiseptik gerekmez, sade su yeterli.\n\n"
            "**Doktor kontrolleri:** 1. hafta, 1. ay, 2. ay, 3. ay rutin kontroller. "
            "Aşı takvimi 2. aydan başlar.",
            GuideCategory.NEWBORN,
        ),
        (
            "3-6-ay-gelisim-rehberi",
            "3-6 ay: gelişim ve etkileşim",
            "Sosyal gülümseme, baş kontrolü ve nesnelere uzanma — bu dönemin "
            "kilit milestone'ları.",
            "3-6 ay arası bebek aktif olarak çevresine tepki vermeye başlar.\n\n"
            "**Beklenen gelişimler:** Sosyal gülümseme, yüksek sesli kahkaha, "
            "başını destek almadan dik tutma, sırtüstünden yan dönme, nesnelere "
            "uzanma.\n\n"
            "**Tummy time** günde toplam 30+ dakika hedeflenebilir; boyun ve sırt "
            "kaslarını güçlendirir.\n\n"
            "**Ek gıda hazırlık dönemi.** 6 ay civarına yaklaştıkça pediatristle "
            "ek gıda zamanlamasını netleştir.",
            GuideCategory.INFANT,
        ),
        (
            "6-12-ay-ek-gida-ve-hareket",
            "6-12 ay: ek gıda ve mobilite",
            "Ek gıdaya geçiş, oturma, emekleme ve ilk adımlar — yoğun motor "
            "gelişim dönemi.",
            "6-12 ay arası bebeğin **fiziksel mobilitesi** patlar.\n\n"
            "**Ek gıda:** Tek gıdalı, az miktarda başla. Önce sebze püresi, sonra "
            "meyve, sonra et ve tahıllar. Bal 1 yaşından önce verilmez.\n\n"
            "**Motor gelişim:** 6-7 ay desteksiz oturma, 8-10 ay emekleme, 9-12 ay "
            "tutunarak ayağa kalkma, 12 ay civarı ilk adımlar.\n\n"
            "**Ev güvenliği:** Köşe yumuşatıcı, dolap kilitleri, priz kapakları "
            "bu dönemde kritik.",
            GuideCategory.OLDER_INFANT,
        ),
        (
            "12-ay-ustu-yurume-ve-konusma",
            "12+ ay: yürüme ve konuşma",
            "İlk kelimeler, bağımsız yürüyüş, kendini ifade etme — yürüme sonrası "
            "dönemin temel başlıkları.",
            "12 ay sonrası bebekten 'yürüyüp konuşan bir insana' geçiş başlar.\n\n"
            "**Konuşma:** 12-15 ay ilk anlamlı kelimeler ('mama', 'baba'). 18 ayda "
            "10-25 kelime tipik. 2 yaşa kadar 50+ kelime ve iki kelimeli cümleler.\n\n"
            "**Yürüme:** 12-18 ay arası geniş normal aralık. Geç yürüyen "
            "çocuklar için 18 ay sonrası pediatristle değerlendirme önerilir.\n\n"
            "**Rutin ve sınırlar:** Bu yaşta tutarlı, kısa ve açık talimatlar "
            "çocuğun güvenlik hissini artırır.",
            GuideCategory.TODDLER,
        ),
    ]

    rows = [
        GuideArticle(
            author_id=admin.id,
            slug=slug,
            title=title,
            summary=summary,
            body=body,
            category=cat,
        )
        for (slug, title, summary, body, cat) in items
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
