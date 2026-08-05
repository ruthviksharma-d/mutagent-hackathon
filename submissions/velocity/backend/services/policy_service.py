"""Data access for admin-managed policies (used by the Policy Engine)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.policy import Policy


def get_enabled_policies(db: Session) -> list[Policy]:
    """Lower `priority` value = evaluated first (higher precedence)."""
    return list(db.scalars(select(Policy).where(Policy.enabled.is_(True)).order_by(Policy.priority.asc())).all())
