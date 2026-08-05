"""Schemas for GET/PUT /api/settings and the company-keyword sub-resource."""
from pydantic import BaseModel, Field


class OrgSettingsOut(BaseModel):
    model_config = {"from_attributes": True}

    organization_name: str
    risk_threshold: int
    supported_websites: list[str]
    allowed_file_types: list[str]
    theme_default: str
    # Mutagent: configurable per-analyzer risk weights and enabled analyzers
    risk_weights: dict[str, float] | None = None
    enabled_analyzers: list[str] | None = None


class OrgSettingsUpdate(BaseModel):
    organization_name: str | None = Field(None, min_length=1, max_length=200)
    risk_threshold: int | None = Field(None, ge=0, le=100)
    supported_websites: list[str] | None = None
    allowed_file_types: list[str] | None = None
    theme_default: str | None = Field(None, pattern="^(light|dark)$")
    # Mutagent: admin-tunable via Settings page sliders/toggles
    risk_weights: dict[str, float] | None = None
    enabled_analyzers: list[str] | None = None


class CompanyKeywordOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    keyword: str
    enabled: bool


class CompanyKeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)


class CompanyKeywordUpdate(BaseModel):
    enabled: bool
