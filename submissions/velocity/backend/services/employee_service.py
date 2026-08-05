"""
Employee directory data access. `last_active` and `extension_status` are
derived from real audit_log activity rather than stored on the User model -
the extension itself never reports install/heartbeat status (Milestone 3
deliberately kept the extension's message protocol unchanged), so
"installed and actively protecting this employee" is inferred from
whether we've actually scanned a prompt for them recently.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models.audit_log import AuditLog
from models.user import User, UserRole

ACTIVE_WINDOW = timedelta(days=1)


def _derive_extension_status(prompt_count: int, last_active: datetime | None) -> str:
    if prompt_count == 0 or last_active is None:
        return "not_installed"
    now = datetime.now(timezone.utc)
    last_active_aware = last_active if last_active.tzinfo else last_active.replace(tzinfo=timezone.utc)
    if now - last_active_aware <= ACTIVE_WINDOW:
        return "active"
    return "inactive"


def get_live_extension_status(db: Session, user: User) -> str:
    """
    Single-user version of the same derivation `list_employees` uses,
    for callers (POST /api/auth/register, /login, GET /me) that need one
    user's live status rather than a whole paginated page. The `User.
    extension_status` DB column is never written to anywhere in this
    codebase (the extension has no heartbeat message) - it exists only as
    the SQLAlchemy Enum's storage type. Every caller must go through this
    function or `list_employees` rather than reading the column directly,
    or they'll see the model's default ("not_installed") forever.
    """
    last_active = db.scalar(
        select(func.max(AuditLog.created_at)).where(AuditLog.user_id == user.id)
    )
    return _derive_extension_status(user.prompt_count, last_active)


def list_employees(
    db: Session,
    page: int,
    page_size: int,
    search: str | None,
    department: str | None,
    role: str | None,
) -> tuple[list[dict], int]:
    last_active_subquery = (
        select(AuditLog.user_id, func.max(AuditLog.created_at).label("last_active"))
        .group_by(AuditLog.user_id)
        .subquery()
    )

    query = (
        select(User, last_active_subquery.c.last_active)
        .outerjoin(last_active_subquery, last_active_subquery.c.user_id == User.id)
        .where(User.role != UserRole.ADMIN)
    )
    count_query = select(func.count()).select_from(User).where(User.role != UserRole.ADMIN)

    if search:
        like = f"%{search}%"
        clause = or_(User.full_name.ilike(like), User.email.ilike(like))
        query = query.where(clause)
        count_query = count_query.where(clause)
    if department:
        query = query.where(User.department.ilike(f"%{department}%"))
        count_query = count_query.where(User.department.ilike(f"%{department}%"))
    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    total = db.scalar(count_query) or 0

    query = query.order_by(User.full_name.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(query).all()

    items = [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "department": user.department,
            "role": user.role.value,
            "prompt_count": user.prompt_count,
            "violation_count": user.violation_count,
            "last_active": last_active,
            "extension_status": _derive_extension_status(user.prompt_count, last_active),
        }
        for user, last_active in rows
    ]
    return items, total
