from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AlbumBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class AlbumCreate(AlbumBase):
    pass


class AlbumUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    cover_object_key: str | None = Field(default=None, max_length=500)


class AlbumOut(AlbumBase):
    id: int
    baby_id: int
    cover_url: str | None
    entries_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
