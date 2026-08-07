"""Schemas backing routers/vscode.py - additive-only, introduced for the
VS Code / Antigravity IDE extension client. See that router's module
docstring for why this endpoint exists separately from schemas/policies.py.
"""
from pydantic import BaseModel


class PolicySummaryItem(BaseModel):
    name: str
    detection_type: str
    action: str  # ALLOW | WARN | REDACT | BLOCK
    priority: int


class PolicySummaryResponse(BaseModel):
    policies: list[PolicySummaryItem] = []
