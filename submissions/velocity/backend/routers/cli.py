"""
POST /api/cli/scan - isolated API endpoint consumed by the PromptShield CLI wrapper (psh).

Reuses the core PromptShield scanning pipeline, Mutagent InvestigationEngine,
and audit log system without touching or modifying any browser extension APIs.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.pipeline import run_pipeline_for_user
from auth.security import decode_access_token
from database import get_db
from models.user import User, UserRole
from schemas.scan import ScanRequest, ScanResponse, TriggeredRule
from services.audit_service import log_scan

router = APIRouter(prefix="/api/cli", tags=["CLI Scan"])


def get_cli_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate CLI user via Bearer token if provided.
    If no header is provided (local CLI usage default), resolves the default admin or first active user.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user = db.get(User, payload["sub"])
            if user and user.is_active:
                return user

    # Fallback for local CLI dev: resolve default admin user or first active user
    user = db.scalar(select(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True)))
    if not user:
        user = db.scalar(select(User).where(User.is_active.is_(True)))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active user available for CLI scan session",
        )
    return user


@router.post("/scan", response_model=ScanResponse)
def scan_cli_prompt(
    payload: ScanRequest,
    current_user: User = Depends(get_cli_user),
    db: Session = Depends(get_db),
):
    """
    Scans CLI prompts & attached files using the exact same security pipeline
    as the browser extension.
    """
    output = run_pipeline_for_user(
        db=db,
        user=current_user,
        prompt=payload.prompt,
        site=payload.site,
        files=payload.files,
    )
    decision = output.decision

    audit_entry = log_scan(
        db=db,
        user=current_user,
        site=payload.site,
        original_prompt=payload.prompt,
        sanitized_prompt=output.sanitized_prompt,
        decision=decision,
        file_findings=output.file_findings,
    )

    return ScanResponse(
        decision=decision.action.value,
        risk=decision.risk.value,
        score=decision.score,
        reason=decision.reason,
        sanitized_prompt=output.sanitized_prompt,
        findings=[TriggeredRule(**rule) for rule in decision.triggered_rules],
        file_findings=output.file_findings,
    )
