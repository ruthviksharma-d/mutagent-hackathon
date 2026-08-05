"""
Analyzers sub-package — one file per analyzer, auto-discovered by the engine.

Public surface:
    from mutagent.analyzers.base import BaseAnalyzer
    from mutagent.analyzers.pii_analyzer import PiiAnalyzer
    # etc.

Adding a new analyzer:
    1. Create mutagent/analyzers/my_analyzer.py with a class MyAnalyzer(BaseAnalyzer)
    2. That's it — the engine auto-discovers it via _build_registry() in engine.py
"""
