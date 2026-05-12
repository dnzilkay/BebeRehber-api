from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.community_post import CommunityCategory


class CommunityAuthor(BaseModel):
    id: int
    name: str
    role: str


class CommunityCommentOut(BaseModel):
    id: int
    post_id: int
    body: str
    author: CommunityAuthor
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommunityCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommunityPostBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20_000)
    category: CommunityCategory = CommunityCategory.GENERAL


class CommunityPostCreate(CommunityPostBase):
    pass


class CommunityPostOut(CommunityPostBase):
    id: int
    author: CommunityAuthor
    is_expert: bool
    comments_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommunityPostDetailOut(CommunityPostOut):
    comments: list[CommunityCommentOut] = []
