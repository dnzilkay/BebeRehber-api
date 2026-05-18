"""Kural-tabanlı (rule-based) ebeveyn öneri motoru — Premium özelliği.

Bebeğin yaşı + son 7 günün bakım pattern'lerine bakarak basit, açıklanabilir
öneriler üretir. Tıbbi tavsiye değildir — sadece "şuna dikkat et" tarzı
kaba sinyallerdir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.baby import Baby
from app.models.care_log import CareKind, CareLog
from app.models.milestone import Milestone
from app.schemas.suggestion import Suggestion


# ---- Yaş bazlı milestone presetleri --------------------------------------
# (preset_id, başlık, açıklama, tipik ay aralığı [start, end])
_AGE_MILESTONE_PRESETS: list[tuple[str, str, str, tuple[int, int]]] = [
    (
        "social_smile",
        "İlk sosyal gülümseme",
        "Çoğu bebek 2 aylık civarında ebeveyne gerçek bir gülümseme verir. "
        "Henüz kaydetmediysen, göz teması anlarına dikkat et.",
        (2, 3),
    ),
    (
        "head_control",
        "Başını destekli tutar",
        "3 ay civarında bebekler kısa süre başlarını dik tutabilir. "
        "Tummy time bunu hızlandırır.",
        (2, 4),
    ),
    (
        "rolls_over",
        "Yana / sırtüstüne dönüş",
        "4-5 ay arası bebekler sırtüstünden yan/yüz üstüne dönmeye başlar.",
        (4, 6),
    ),
    (
        "sits_supported",
        "Destekli oturuş",
        "6 ay civarında bebekler kısa süre destekli oturabilir.",
        (5, 7),
    ),
    (
        "crawls",
        "Emekleme",
        "8-10 ay arası tipik. Bazı bebekler atlayıp doğrudan ayağa kalkabilir.",
        (8, 11),
    ),
    (
        "stands_with_support",
        "Tutunarak ayağa kalkar",
        "9-12 ay arası mobilyalardan destek alarak ayağa kalkar.",
        (9, 13),
    ),
    (
        "first_steps",
        "İlk adımlar",
        "12 ay civarı tipik. 9-18 ay arası geniş normal aralıktır.",
        (11, 16),
    ),
    (
        "first_word",
        "İlk anlamlı kelime",
        "10-14 ay arası 'mama', 'baba' gibi anlam taşıyan kelime gelir.",
        (10, 15),
    ),
]


# ---- Yaşa göre önerilen aralıklar ---------------------------------------


def _recommended_sleep_hours(age_months: int) -> tuple[float, float]:
    """Yaş aya göre günlük önerilen uyku aralığı (alt, üst)."""
    if age_months < 1:
        return 14.0, 17.0
    if age_months < 4:
        return 12.0, 16.0
    if age_months < 12:
        return 12.0, 15.0
    if age_months < 24:
        return 11.0, 14.0
    return 10.0, 13.0


def _recommended_feeding_count(age_months: int) -> tuple[int, int]:
    """Yaş aya göre günlük önerilen besleme sayısı (alt, üst)."""
    if age_months < 4:
        return 6, 10
    if age_months < 6:
        return 5, 8
    if age_months < 12:
        return 4, 6
    return 3, 5


def _recommended_diaper_count(age_months: int) -> int:
    """Yaş aya göre günlük minimum bez sayısı (alt sınır)."""
    if age_months < 6:
        return 6
    if age_months < 12:
        return 5
    return 4


# ---- Yardımcılar ---------------------------------------------------------


def _age_in_months(birth: date, today: date) -> int:
    return (
        (today.year - birth.year) * 12
        + (today.month - birth.month)
        - (1 if today.day < birth.day else 0)
    )


@dataclass
class _Window:
    sleep_minutes: int
    feeding_count: int
    diaper_count: int
    days: int

    @property
    def avg_sleep_hours(self) -> float:
        if self.days == 0:
            return 0.0
        return self.sleep_minutes / 60 / self.days

    @property
    def avg_feeding(self) -> float:
        if self.days == 0:
            return 0.0
        return self.feeding_count / self.days

    @property
    def avg_diaper(self) -> float:
        if self.days == 0:
            return 0.0
        return self.diaper_count / self.days


def _build_window(db: Session, baby_id: int, days: int) -> _Window:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    logs = list(
        db.execute(
            select(CareLog)
            .where(CareLog.baby_id == baby_id)
            .where(CareLog.started_at >= cutoff)
        ).scalars()
    )
    sleep_minutes = 0
    feeding_count = 0
    diaper_count = 0
    for log in logs:
        if log.kind == CareKind.SLEEP and log.ended_at is not None:
            sleep_minutes += int((log.ended_at - log.started_at).total_seconds() // 60)
        elif log.kind == CareKind.FEEDING:
            feeding_count += 1
        elif log.kind == CareKind.DIAPER:
            diaper_count += 1
    return _Window(
        sleep_minutes=sleep_minutes,
        feeding_count=feeding_count,
        diaper_count=diaper_count,
        days=days,
    )


# ---- Ana giriş -----------------------------------------------------------


def build_suggestions(db: Session, baby: Baby) -> list[Suggestion]:
    today = date.today()
    age_months = _age_in_months(baby.birth_date, today)
    suggestions: list[Suggestion] = []

    # Milestone önerileri: yaş aralığı içinde olan ama henüz kaydedilmemiş
    recorded_presets: set[str] = set(
        db.execute(
            select(Milestone.preset_id)
            .where(Milestone.baby_id == baby.id)
            .where(Milestone.preset_id.isnot(None))
        )
        .scalars()
        .all()
    )
    for preset_id, title, body, (start, end) in _AGE_MILESTONE_PRESETS:
        if preset_id in recorded_presets:
            continue
        if start <= age_months <= end:
            suggestions.append(
                Suggestion(
                    id=f"milestone_{preset_id}",
                    category="milestone",
                    severity="info",
                    title=f"{title} — bu döneme denk gelir",
                    body=body,
                )
            )

    # Bakım pattern önerileri — son 7 gün
    window = _build_window(db, baby.id, days=7)
    if window.feeding_count > 0 or window.diaper_count > 0 or window.sleep_minutes > 0:
        sleep_low, sleep_high = _recommended_sleep_hours(age_months)
        if window.avg_sleep_hours and window.avg_sleep_hours < sleep_low - 1:
            suggestions.append(
                Suggestion(
                    id="sleep_low",
                    category="sleep",
                    severity="watch",
                    title="Uyku saatleri azalmış olabilir",
                    body=(
                        f"Son 7 günün ortalaması {window.avg_sleep_hours:.1f} sa/gün. "
                        f"{age_months} aylık bir bebek için {sleep_low:.0f}-{sleep_high:.0f} sa "
                        f"önerilir. Akşam rutini ve uyku ortamını gözden geçirmek faydalı olabilir."
                    ),
                )
            )

        feed_low, feed_high = _recommended_feeding_count(age_months)
        if window.avg_feeding and window.avg_feeding < feed_low - 1:
            suggestions.append(
                Suggestion(
                    id="feeding_low",
                    category="feeding",
                    severity="watch",
                    title="Besleme sıklığı düşmüş görünüyor",
                    body=(
                        f"Son 7 günde günlük ortalama {window.avg_feeding:.1f} besleme. "
                        f"{age_months} aylık bebekler için tipik aralık günde {feed_low}-{feed_high}. "
                        f"Kayıtları eksik tutuyor olabilirsin; ya da pediatrist görüşü iyi olur."
                    ),
                )
            )

        diaper_min = _recommended_diaper_count(age_months)
        if 0 < window.avg_diaper < diaper_min - 1:
            suggestions.append(
                Suggestion(
                    id="diaper_low",
                    category="diaper",
                    severity="watch",
                    title="Bez sayısı az olabilir",
                    body=(
                        f"Son 7 günde günlük ortalama {window.avg_diaper:.1f} bez. "
                        f"{age_months} aylık bebek için günde {diaper_min}+ ıslak bez "
                        f"önerilir. Sıvı alımını kontrol et."
                    ),
                )
            )
    else:
        # Hiç kayıt yoksa kayıt tutma ipucu
        suggestions.append(
            Suggestion(
                id="logging_tip",
                category="tip",
                severity="tip",
                title="Son 7 günde bakım kaydı yok",
                body=(
                    "Düzenli kayıt tutmak hem doktorla iletişimi kolaylaştırır "
                    "hem de pattern'leri görmenizi sağlar. Dashboard'dan hızlı "
                    "ekleme ile birkaç gün dene."
                ),
            )
        )

    # Yaş bazlı genel ipucu (her zaman en sonda)
    age_tip = _age_tip(age_months)
    if age_tip:
        suggestions.append(age_tip)

    return suggestions


def _age_tip(age_months: int) -> Suggestion | None:
    if age_months < 1:
        return Suggestion(
            id="tip_newborn",
            category="tip",
            severity="tip",
            title="Yenidoğan dönemi",
            body="2-3 saatte bir besleme normaldir. Tummy time'a alıştır.",
        )
    if age_months < 4:
        return Suggestion(
            id="tip_3m",
            category="tip",
            severity="tip",
            title="Gülümseme ve etkileşim dönemi",
            body="Yüz yüze konuşma, taklit oyunları sosyal gelişimi hızlandırır.",
        )
    if age_months < 7:
        return Suggestion(
            id="tip_6m",
            category="tip",
            severity="tip",
            title="Ek gıdaya hazırlık",
            body="6 ay civarı tek gıdalı, az miktarda ek gıda başlangıcı önerilir. "
            "Pediatrist ile zamanlamayı netleştir.",
        )
    if age_months < 13:
        return Suggestion(
            id="tip_1y",
            category="tip",
            severity="tip",
            title="Hareket dönemi",
            body="Evde köşeler, kabin kilitleri, tutunma yerleri için güvenlik kontrolü "
            "iyi bir zamanlama.",
        )
    return Suggestion(
        id="tip_toddler",
        category="tip",
        severity="tip",
        title="Yürüme sonrası dönem",
        body="Rutin ve sınırlar bu yaşta önemli. Kısa, açık talimatlar işe yarar.",
    )
