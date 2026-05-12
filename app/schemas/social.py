from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.social_post import SocialPlatform, SocialPostStatus


class SocialPostBase(BaseModel):
    platform: SocialPlatform
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=10_000)
    image_url: str | None = Field(default=None, max_length=500)
    scheduled_for: datetime | None = None
    status: SocialPostStatus = SocialPostStatus.DRAFT


class SocialPostCreate(SocialPostBase):
    pass


class SocialPostUpdate(BaseModel):
    platform: SocialPlatform | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=10_000)
    image_url: str | None = Field(default=None, max_length=500)
    scheduled_for: datetime | None = None
    status: SocialPostStatus | None = None
    likes: int | None = Field(default=None, ge=0)
    comments_count: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    reach: int | None = Field(default=None, ge=0)


class SocialPostOut(SocialPostBase):
    id: int
    likes: int
    comments_count: int
    shares: int
    reach: int
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SocialStatsOut(BaseModel):
    total_posts: int
    drafts: int
    scheduled: int
    published: int
    total_reach: int
    total_engagement: int  # likes + comments + shares
