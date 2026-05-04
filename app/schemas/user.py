from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserPlan, UserRole


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserOut(UserBase):
    id: int
    plan: UserPlan
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
