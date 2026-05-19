from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.media_asset import MediaKind
from app.schemas.audit import ActorOut


class MediaAssetOut(BaseModel):
    id: int
    entry_id: int
    kind: MediaKind
    content_type: str
    size_bytes: int
    duration_sec: int | None
    url: str
    created_at: datetime
    created_by: ActorOut | None = None

    model_config = ConfigDict(from_attributes=True)
