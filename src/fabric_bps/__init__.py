"""Fabric Best Practices Scanner.

Evaluate a Microsoft Fabric tenant against a contextual best-practices catalog and produce
prioritized, evidence-backed governance findings tailored to your environment, with near-zero
manual input. Each best practice is a rule with an applicability condition + an evidence
check; the engine reports discrete, evidence-backed findings you can act on.

Quickstart (offline / testing):
    from fabric_bps import scan_from_signals
    result = scan_from_signals(signals_dict)

Quickstart (in a Fabric notebook):
    from fabric_bps import scan
    from fabric_bps.collectors import fabric_notebook_token_provider
    result = scan(fabric_notebook_token_provider(), write="lakehouse", spark=spark)
"""
from __future__ import annotations

from . import checks  # noqa: F401  (imported for side effect: registers check primitives)
from .archetype import classify
from .catalog import load_catalog
from .engine import evaluate
from .models import Finding, Impact, Rule, Severity, Status
from .run import scan, scan_from_signals
from .signals import Signals

__version__ = "0.1.0"

__all__ = [
    "scan",
    "scan_from_signals",
    "load_catalog",
    "classify",
    "evaluate",
    "Signals",
    "Finding",
    "Rule",
    "Status",
    "Impact",
    "Severity",
    "__version__",
]
