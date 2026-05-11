from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.milestone import MilestoneCategory


class MilestoneBase(BaseModel):
    preset_id: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    category: MilestoneCategory = MilestoneCategory.OTHER
    reached_on: date
    note: str | None = Field(default=None, max_length=500)


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    category: MilestoneCategory | None = None
    reached_on: date | None = None
    note: str | None = Field(default=None, max_length=500)


class MilestoneOut(MilestoneBase):
    id: int
    baby_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
