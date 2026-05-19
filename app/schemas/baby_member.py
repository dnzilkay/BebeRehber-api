from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.baby_member import BabyMemberRole, BabyRelationship


class BabyMemberOut(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    role: BabyMemberRole
    relationship: BabyRelationship | None = None
    relationship_label: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BabyMemberRelationshipUpdate(BaseModel):
    """Üyenin bebek için aile rolünü günceller. Sadece kullanıcı kendisini
    güncelleyebilir (veya admin). owner/co_parent rolü değişmez."""

    relationship: BabyRelationship | None = None
    relationship_label: str | None = Field(default=None, max_length=60)
