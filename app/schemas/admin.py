from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserPlan, UserRole


class AdminUserOut(BaseModel):
    id: int
    email: str
    name: str
    plan: UserPlan
    role: UserRole
    is_active: bool
    created_at: datetime
    baby_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AdminUserUpdate(BaseModel):
    plan: UserPlan | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    premium_users: int
    admin_users: int
    new_users_last_7_days: int
    total_babies: int
    total_journal_entries: int
    total_media: int
    total_community_posts: int
    expert_posts: int
    total_community_comments: int

    model_config = ConfigDict(from_attributes=True)
