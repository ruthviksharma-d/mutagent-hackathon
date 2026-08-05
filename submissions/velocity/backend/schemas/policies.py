"""CRUD schemas for the Policies page."""
from datetime import datetime

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: str = ""
    priority: int = 100
    detection_type: str
    action: str = Field(..., pattern="^(ALLOW|WARN|REDACT|BLOCK)$")
    enabled: bool = True


class PolicyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    priority: int | None = None
    detection_type: str | None = None
    action: str | None = Field(None, pattern="^(ALLOW|WARN|REDACT|BLOCK)$")
    enabled: bool | None = None


class PolicyOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    description: str
    priority: int
    detection_type: str
    action: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
