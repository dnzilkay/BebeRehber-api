from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BabyInviteOut(BaseModel):
    token: str
    url: str
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BabyInviteAcceptOut(BaseModel):
    baby_id: int
    baby_name: str
