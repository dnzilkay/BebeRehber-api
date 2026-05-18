from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.guide_article import GuideCategory


class GuideArticleBase(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    summary: str = Field(min_length=10, max_length=300)
    body: str = Field(min_length=20)
    category: GuideCategory


class GuideArticleCreate(GuideArticleBase):
    # Slug opsiyonel: verilmezse title'dan türetilir
    slug: str | None = Field(default=None, min_length=3, max_length=160)


class GuideArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    summary: str | None = Field(default=None, min_length=10, max_length=300)
    body: str | None = Field(default=None, min_length=20)
    category: GuideCategory | None = None


class GuideArticleSummary(BaseModel):
    """Liste görünümünde body atılır."""

    id: int
    slug: str
    title: str
    summary: str
    category: GuideCategory
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuideArticleOut(GuideArticleSummary):
    body: str
