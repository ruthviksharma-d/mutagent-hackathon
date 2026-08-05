"""Schemas for GET /api/employees."""
from datetime import datetime

from pydantic import BaseModel


class EmployeeListItem(BaseModel):
    id: str
    full_name: str
    email: str
    department: str | None
    role: str
    prompt_count: int
    violation_count: int
    last_active: datetime | None
    extension_status: str  # active | inactive | not_installed - derived from activity, see employee_service.py


class EmployeeListResponse(BaseModel):
    items: list[EmployeeListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
