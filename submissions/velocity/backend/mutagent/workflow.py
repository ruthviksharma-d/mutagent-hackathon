"""
Workflow — defines the execution graph for the investigation engine.

Stages run in order. Analyzers within a parallel stage run concurrently
using ThreadPoolExecutor (no async changes to FastAPI routes needed, since
all detectors are sync/CPU-bound).

Per-analyzer timeout: each analyzer in a parallel stage is given
DEFAULT_ANALYZER_TIMEOUT_SECONDS before it is marked TIMEOUT and the
investigation continues with reduced confidence.

Execution graph:
    Stage 1 [sequential]: ContextAnalyzer
    Stage 2 [sequential]: FileIntelAnalyzer
    Stage 3 [parallel]:   PiiAnalyzer | SecretsAnalyzer |
                          InjectionAnalyzer | ComplianceAnalyzer
    Stage 4 [sequential]: RiskFusionAnalyzer
    Stage 5 [sequential]: DecisionAnalyzer

Adding a new stage or analyzer: add it to WORKFLOW below.
No engine.py changes required if it auto-registers via the class registry.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Stage:
    """A named group of analyzers that run together (sequentially or in parallel)."""
    name: str
    analyzers: list[str]         # Analyzer class names
    parallel: bool = False       # True = run analyzers concurrently


# The canonical workflow for every PromptShield investigation.
# Stages execute in list order.
WORKFLOW: list[Stage] = [
    Stage(
        name="context",
        analyzers=["ContextAnalyzer"],
        parallel=False,
    ),
    Stage(
        name="extraction",
        analyzers=["FileIntelAnalyzer"],
        parallel=False,
    ),
    Stage(
        name="analysis",
        analyzers=[
            "PiiAnalyzer",
            "SecretsAnalyzer",
            "InjectionAnalyzer",
            "ComplianceAnalyzer",
        ],
        parallel=True,          # these four run concurrently
    ),
    Stage(
        name="fusion",
        analyzers=["RiskFusionAnalyzer"],
        parallel=False,
    ),
    Stage(
        name="decision",
        analyzers=["DecisionAnalyzer"],
        parallel=False,
    ),
]
