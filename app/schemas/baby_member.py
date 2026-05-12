from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.baby_member import BabyMemberRole


class BabyMemberOut(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    role: BabyMemberRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
