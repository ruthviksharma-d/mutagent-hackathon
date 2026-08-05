"""Employees API: searchable/filterable/paginated directory for the Employees page."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth.dependencies import require_analyst_or_admin
from database import get_db
from models.user import User
from schemas.employees import EmployeeListItem, EmployeeListResponse
from services.employee_service import list_employees

router = APIRouter(prefix="/api/employees", tags=["Employees"])


@router.get("", response_model=EmployeeListResponse)
def get_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    department: str | None = None,
    role: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_analyst_or_admin),
):
    items, total = list_employees(db, page, page_size, search, department, role)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return EmployeeListResponse(
        items=[EmployeeListItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
