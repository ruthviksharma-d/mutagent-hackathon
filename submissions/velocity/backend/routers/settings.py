"""
Settings API: the singleton OrgSettings row (org name, risk threshold,
supported websites, allowed file types, default theme) plus CRUD for
company-sensitive keywords (reusing the CompanyKeyword table
ai/keyword_detector.py already reads from - Milestone 4 only adds an
admin-facing API on top, it doesn't touch the detector itself).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import require_admin, require_analyst_or_admin
from database import get_db
from models.company_keyword import CompanyKeyword
from models.user import User
from schemas.settings import (
    CompanyKeywordCreate,
    CompanyKeywordOut,
    CompanyKeywordUpdate,
    OrgSettingsOut,
    OrgSettingsUpdate,
)
from services.settings_service import get_or_create_settings

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=OrgSettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_analyst_or_admin),
):
    return get_or_create_settings(db)


@router.put("", response_model=OrgSettingsOut)
def update_settings(
    payload: OrgSettingsUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    settings = get_or_create_settings(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/keywords", response_model=list[CompanyKeywordOut])
def list_keywords(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_analyst_or_admin),
):
    return list(db.scalars(select(CompanyKeyword).order_by(CompanyKeyword.keyword.asc())).all())


@router.post("/keywords", response_model=CompanyKeywordOut, status_code=status.HTTP_201_CREATED)
def create_keyword(
    payload: CompanyKeywordCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    existing = db.scalar(select(CompanyKeyword).where(CompanyKeyword.keyword == payload.keyword))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Keyword already exists")
    keyword = CompanyKeyword(keyword=payload.keyword, enabled=True)
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


@router.patch("/keywords/{keyword_id}", response_model=CompanyKeywordOut)
def update_keyword(
    keyword_id: str,
    payload: CompanyKeywordUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    keyword = db.get(CompanyKeyword, keyword_id)
    if keyword is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    keyword.enabled = payload.enabled
    db.commit()
    db.refresh(keyword)
    return keyword


@router.delete("/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword(
    keyword_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    keyword = db.get(CompanyKeyword, keyword_id)
    if keyword is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    db.delete(keyword)
    db.commit()
