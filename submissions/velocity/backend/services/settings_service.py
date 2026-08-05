"""Data access for the singleton OrgSettings row."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.settings import OrgSettings


def get_or_create_settings(db: Session) -> OrgSettings:
    settings = db.scalar(select(OrgSettings))
    if settings is None:
        settings = OrgSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings
