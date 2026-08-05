"""Company-specific sensitive terms flagged by the Company Keyword Detector."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CompanyKeyword(Base):
    __tablename__ = "company_keywords"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    keyword: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
