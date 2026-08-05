"""
InvestigationContext builder — fetches all DB state once upfront and
assembles the InvestigationContext that flows through the entire
investigation.

This is the only place in the mutagent package that reads from the
database at construction time. Analyzers never touch the DB.
"""
from __future__ import annotations

import uuid
import logging

from sqlalchemy.orm import Session

from models.user import User
from mutagent.models import (
    DEFAULT_RISK_WEIGHTS,
    InvestigationContext,
)
from schemas.scan import ScanFileInput
from services.keyword_service import get_enabled_keywords
from services.policy_service import get_enabled_policies
from services.settings_service import get_or_create_settings

logger = logging.getLogger("promptshield.mutagent.context")


def build_context(
    db: Session,
    user: User,
    prompt: str,
    site: str,
    files: list[ScanFileInput],
) -> InvestigationContext:
    """
    Build a fully-populated InvestigationContext for one scan request.

    All database reads happen here — analyzers receive a context object
    and never query the DB themselves.
    """
    scan_id = str(uuid.uuid4())

    keywords = get_enabled_keywords(db)
    policies = get_enabled_policies(db)
    org_settings = get_or_create_settings(db)

    # Risk weights: load from OrgSettings if configured, else use defaults.
    stored_weights: dict | None = getattr(org_settings, "risk_weights", None)
    risk_weights: dict[str, float] = {**DEFAULT_RISK_WEIGHTS}
    if stored_weights and isinstance(stored_weights, dict):
        risk_weights.update({k: float(v) for k, v in stored_weights.items()})

    # Enabled analyzers: empty set means "all enabled".
    stored_enabled: list | None = getattr(org_settings, "enabled_analyzers", None)
    enabled_analyzers: set[str] = set()
    if stored_enabled and isinstance(stored_enabled, list):
        enabled_analyzers = set(stored_enabled)

    logger.debug(
        "Built InvestigationContext scan_id=%s user=%s analyzers_enabled=%s",
        scan_id,
        user.email,
        enabled_analyzers or "all",
    )

    return InvestigationContext(
        scan_id=scan_id,
        user=user,
        browser=site,
        raw_prompt=prompt,
        uploaded_files=files,
        keywords=keywords,
        policies=policies,
        org_settings=org_settings,
        risk_weights=risk_weights,
        enabled_analyzers=enabled_analyzers,
    )
