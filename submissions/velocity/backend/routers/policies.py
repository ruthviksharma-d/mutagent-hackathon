"""
Policies API: full CRUD over the Policy table backing ai/policy_engine.py.
Reads are available to admin + security_analyst; writes (create/update/
delete) are admin-only, since a policy misconfiguration directly changes
what the AI Detection Engine blocks or allows org-wide.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import require_admin, require_analyst_or_admin
from database import get_db
from models.policy import Policy
from models.user import User
from schemas.policies import PolicyCreate, PolicyOut, PolicyUpdate

router = APIRouter(prefix="/api/policies", tags=["Policies"])


@router.get("", response_model=list[PolicyOut])
def list_policies(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_analyst_or_admin),
):
    policies = db.scalars(select(Policy).order_by(Policy.priority.asc())).all()
    return list(policies)


@router.post("", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    policy = Policy(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def _get_policy_or_404(db: Session, policy_id: str) -> Policy:
    policy = db.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.patch("/{policy_id}", response_model=PolicyOut)
def update_policy(
    policy_id: str,
    payload: PolicyUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    policy = _get_policy_or_404(db, policy_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    policy = _get_policy_or_404(db, policy_id)
    db.delete(policy)
    db.commit()
