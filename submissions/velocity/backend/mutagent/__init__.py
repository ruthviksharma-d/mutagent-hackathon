"""
Mutagent — Multi-Analyzer Orchestration Engine for PromptShield AI.

This package replaces the sequential scan pipeline with a modular,
extensible, observable investigation engine. Each detection concern is
handled by a dedicated Analyzer that shares a single InvestigationContext.

Public surface:
    from mutagent.engine import InvestigationEngine
    output = InvestigationEngine(db).run(user=user, prompt=..., site=..., files=...)

The engine is called from ai/pipeline.py (run_pipeline_for_user) so the
public API contract for routers/scan.py is unchanged.
"""
from mutagent.engine import InvestigationEngine  # noqa: F401

__all__ = ["InvestigationEngine"]
