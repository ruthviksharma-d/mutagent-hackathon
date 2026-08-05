"""Pydantic request/response schemas for authentication."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

from models.user import UserRole


class UserCreate(BaseModel):
    """
    Public self-registration payload. Deliberately has NO `role` field -
    POST /api/auth/register always creates a plain employee account
    (see routers/auth.py). A client can never request an elevated role
    through this endpoint.
    """

    email: EmailStr
    full_name: str
    password: str
    department: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    department: str | None
    is_active: bool
    # str, not the ExtensionStatus DB enum: this is always overwritten with
    # a live-derived value by routers/auth.py (see
    # services/employee_service.get_live_extension_status) before the
    # response is returned - the raw DB column is never written to and
    # would otherwise always read "not_installed". Typed as `str` here to
    # match EmployeeListItem.extension_status, which is derived the same
    # way for the same reason.
    extension_status: str
    prompt_count: int
    violation_count: int
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int
