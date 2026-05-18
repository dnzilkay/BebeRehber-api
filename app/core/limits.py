"""Free vs Premium plan sınırları (proje.md kapsamına uygun).

Free pakette:
- En fazla 3 albüm
- Albüm başına 30 medya
- Video uzunluğu ≤ 30 saniye
- Veri geçmişi son 14 gün

Premium pakette:
- Sınırsız albüm / medya
- Video uzunluğu ≤ 180 saniye (3 dakika)
- Veri geçmişi son 365 gün (detaylı analiz)
"""

from sqlalchemy.orm import Session

from app.models.baby import Baby
from app.models.user import User, UserPlan, UserRole


FREE_MAX_ALBUMS = 3
FREE_MAX_MEDIA_PER_ALBUM = 30
FREE_MAX_VIDEO_SEC = 30
PREMIUM_MAX_VIDEO_SEC = 180
FREE_MAX_HISTORY_DAYS = 14
PREMIUM_MAX_HISTORY_DAYS = 365


def is_premium(user: User) -> bool:
    """Premium plan veya admin rolü Premium hakları taşır."""
    return user.plan == UserPlan.PREMIUM or user.role == UserRole.ADMIN


def max_video_seconds(user: User) -> int:
    return PREMIUM_MAX_VIDEO_SEC if is_premium(user) else FREE_MAX_VIDEO_SEC


def max_history_days(user: User) -> int:
    """Plan'a göre maksimum geçmiş veri penceresi (gün)."""
    return PREMIUM_MAX_HISTORY_DAYS if is_premium(user) else FREE_MAX_HISTORY_DAYS


def clamp_history_days(user: User, days: int | None) -> int:
    """`days` istek değerini plan tavanına bağlar; None ise plan tavanı."""
    cap = max_history_days(user)
    if days is None:
        return cap
    return min(max(days, 1), cap)


# ---- Per-baby Premium devri ---------------------------------------------
#
# Proje.md §4.2 Özellik 5: "Aile paylaşımı — aynı bebek profiline birden
# fazla ebeveynin ortak erişimi" Premium'un kendisinin bir parçasıdır.
# Bunun anlamı: Premium owner bir bebeği co-parent ile paylaştığında, co-parent
# o bebek için Premium feature'lara (suggestions, timeline, 30-gün analiz,
# ZIP export) erişebilir. Ama co-parent kendi yeni bir bebek eklerse
# (sahibi olur), o bebek için yine Free kalır.
#
# Community / reklamsız gibi kişi-context Premium feature'lar bu kuraldan
# etkilenmez — kişinin kendi plan'ı geçerlidir.


def is_premium_for_baby(db: Session, user: User, baby_id: int) -> bool:
    """Bu bebek bağlamında Premium hak'ları var mı?

    True döner:
    - Kullanıcı kendi Premium veya admin (kişi-bazlı Premium'u taşır)
    - Bebeğin owner'ı Premium (co-parent için aile paylaşımı devri)
    """
    if is_premium(user):
        return True
    baby = db.get(Baby, baby_id)
    if baby is None or baby.owner is None:
        return False
    return baby.owner.plan == UserPlan.PREMIUM


def max_history_days_for_baby(db: Session, user: User, baby_id: int) -> int:
    """Bebek bağlamında plan tavanı (co-parent için owner premium'u devralır)."""
    if is_premium_for_baby(db, user, baby_id):
        return PREMIUM_MAX_HISTORY_DAYS
    return FREE_MAX_HISTORY_DAYS


def clamp_history_days_for_baby(
    db: Session, user: User, baby_id: int, days: int | None
) -> int:
    cap = max_history_days_for_baby(db, user, baby_id)
    if days is None:
        return cap
    return min(max(days, 1), cap)
