"""
User model. Roles: admin, security_analyst.
Extra fields (department, extension_status, prompt_count, violation_count)
are included now so the Employees dashboard page (later milestone) has
real columns to read from instead of being retrofitted.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SECURITY_ANALYST = "security_analyst"
    EMPLOYEE = "employee"


class ExtensionStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    NOT_INSTALLED = "not_installed"


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    extension_status: Mapped[ExtensionStatus] = mapped_column(
        Enum(ExtensionStatus), default=ExtensionStatus.NOT_INSTALLED, nullable=False
    )
    prompt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    violation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
