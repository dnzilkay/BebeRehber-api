from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.care_log import CareKind, DiaperType


class CareLogBase(BaseModel):
    kind: CareKind
    started_at: datetime
    ended_at: datetime | None = None
    amount_ml: int | None = Field(default=None, ge=0, le=10_000)
    diaper_type: DiaperType | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_kind_fields(self) -> "CareLogBase":
        if self.kind == CareKind.SLEEP:
            if self.ended_at is None:
                raise ValueError("Uyku kaydı için bitiş saati zorunludur.")
            if self.ended_at <= self.started_at:
                raise ValueError("Bitiş saati başlangıçtan sonra olmalı.")
        if self.kind == CareKind.DIAPER and self.diaper_type is None:
            raise ValueError("Bez kaydı için tür seçilmelidir.")
        return self


class CareLogCreate(CareLogBase):
    pass


class CareLogOut(CareLogBase):
    id: int
    baby_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CareSummary(BaseModel):
    """Dashboard için günlük özet."""

    sleep_minutes: int
    feeding_count: int
    feeding_total_ml: int
    diaper_count: int
