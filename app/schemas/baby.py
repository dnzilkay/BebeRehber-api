from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.baby import BabyGender


class BabyBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    birth_date: date
    gender: BabyGender = BabyGender.UNSPECIFIED
    avatar_url: str | None = Field(default=None, max_length=500)


class BabyCreate(BabyBase):
    pass


class BabyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    birth_date: date | None = None
    gender: BabyGender | None = None
    avatar_url: str | None = Field(default=None, max_length=500)


class BabyOut(BabyBase):
    id: int
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
