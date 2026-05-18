from pydantic import BaseModel


class Suggestion(BaseModel):
    """Bebek için tek bir kişiselleştirilmiş öneri."""

    id: str
    category: str  # "milestone" | "sleep" | "feeding" | "diaper" | "tip"
    severity: str  # "info" | "watch" | "tip"
    title: str
    body: str
