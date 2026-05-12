from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.milestone import MilestoneCategory
from app.schemas.media_asset import MediaAssetOut


class TimelineEntry(BaseModel):
    kind: Literal["journal_entry"] = "journal_entry"
    id: int
    date: date
    title: str
    body: str | None = None
    album_id: int | None = None
    album_name: str | None = None
    media: list[MediaAssetOut] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimelineMilestone(BaseModel):
    kind: Literal["milestone"] = "milestone"
    id: int
    date: date
    title: str
    category: MilestoneCategory
    preset_id: str | None = None
    note: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


TimelineItem = TimelineEntry | TimelineMilestone
