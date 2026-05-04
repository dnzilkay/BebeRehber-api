from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.reminder import ReminderKind


class ReminderBase(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    kind: ReminderKind = ReminderKind.GENERAL
    due_at: datetime
    note: str | None = Field(default=None, max_length=500)


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    kind: ReminderKind | None = None
    due_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)
    completed: bool | None = None


class ReminderOut(ReminderBase):
    id: int
    baby_id: int
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
