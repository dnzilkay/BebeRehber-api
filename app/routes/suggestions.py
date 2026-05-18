"""Premium-only kişiselleştirilmiş ebeveyn önerileri."""

from fastapi import APIRouter, HTTPException, status

from app.core.baby_access import ensure_baby_access
from app.core.deps import CurrentUser, DbSession
from app.core.limits import is_premium
from app.core.suggestions import build_suggestions
from app.models.baby import Baby
from app.schemas.suggestion import Suggestion


router = APIRouter(prefix="/babies/{baby_id}/suggestions", tags=["suggestions"])


@router.get(
    "",
    response_model=list[Suggestion],
    summary="Premium: bebek yaşı + son 7 gün pattern'i için öneriler",
)
def get_suggestions(
    baby_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> list[Suggestion]:
    ensure_baby_access(db, current_user.id, baby_id)

    if not is_premium(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Kişiselleştirilmiş öneriler Premium pakette yer alır. "
                "Premium'a geçerek bebeğinin yaşına ve son 7 gün verisine "
                "göre hazırlanmış önerileri gör."
            ),
        )

    baby = db.get(Baby, baby_id)
    assert baby is not None  # ensure_baby_access garantiler
    return build_suggestions(db, baby)
