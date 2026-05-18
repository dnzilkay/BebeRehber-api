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
