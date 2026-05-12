from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.media_asset import MediaAssetOut


class JournalEntryBase(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str | None = Field(default=None, max_length=10_000)
    occurred_on: date
    album_id: int | None = None


class JournalEntryCreate(JournalEntryBase):
    pass


class JournalEntryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    body: str | None = Field(default=None, max_length=10_000)
    occurred_on: date | None = None
    album_id: int | None = None


class JournalEntryOut(JournalEntryBase):
    id: int
    baby_id: int
    created_at: datetime
    media: list[MediaAssetOut] = []

    model_config = ConfigDict(from_attributes=True)
