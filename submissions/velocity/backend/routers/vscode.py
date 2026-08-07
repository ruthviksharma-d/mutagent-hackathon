"""
Additive-only endpoints introduced for the VS Code / Antigravity IDE
extension (submissions/velocity/vscode-extension). Nothing in this file
changes the behavior, routes, or response shapes the browser extension or
CLI depend on - it only adds a new route the existing clients never call.

Why this exists: GET /api/policies (routers/policies.py) is restricted to
admin/security_analyst because it returns full CRUD detail intended for
the Policies management page. The VS Code extension runs as whatever role
the logged-in employee has (usually UserRole.EMPLOYEE) and only needs a
lightweight, read-only summary of currently-enabled policies to populate
its local "policy cache" (used purely for display in the risk panel /
status bar - it never makes an ALLOW/WARN/REDACT/BLOCK decision itself;
every real decision still comes from POST /api/scan, per the project rule
that clients must not duplicate policy/detection logic).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.policy import Policy
from models.user import User
from schemas.vscode import PolicySummaryItem, PolicySummaryResponse

router = APIRouter(prefix="/api/policies", tags=["Policies"])


@router.get("/summary", response_model=PolicySummaryResponse)
def get_policy_summary(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Any authenticated user (any role) can read this - unlike the full
    GET /api/policies list, it deliberately omits `description` and other
    admin-facing detail and only exposes what a client needs to show a
    human-readable "here's what's currently enforced" summary."""
    policies = db.scalars(
        select(Policy).where(Policy.enabled.is_(True)).order_by(Policy.priority.asc())
    ).all()
    return PolicySummaryResponse(
        policies=[
            PolicySummaryItem(
                name=p.name,
                detection_type=p.detection_type,
                action=p.action,
                priority=p.priority,
            )
            for p in policies
        ]
    )
