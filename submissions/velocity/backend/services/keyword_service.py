"""Data access for company-sensitive keywords (used by the Company Keyword Detector)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.company_keyword import CompanyKeyword


def get_enabled_keywords(db: Session) -> list[str]:
    rows = db.scalars(select(CompanyKeyword).where(CompanyKeyword.enabled.is_(True))).all()
    return [row.keyword for row in rows]
