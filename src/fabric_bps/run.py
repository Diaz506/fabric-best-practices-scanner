"""Single-call orchestrators (the Jumpstart-style entry points).

- scan_from_signals(): offline / testable — evaluate a pre-collected signals dict.
- scan():             live — collect from Fabric/Power BI admin APIs, then evaluate.
"""
from __future__ import annotations

import uuid

from .archetype import classify
from .catalog import load_catalog
from .engine import evaluate
from .signals import Signals


def scan_from_signals(
    signals_dict: dict,
    dimensions=None,
    context_overrides: dict = None,
    run_id: str = None,
    ai_rationale: bool = False,
) -> dict:
    run_id = run_id or uuid.uuid4().hex[:12]
    signals = Signals.from_dict(signals_dict)
    context = classify(signals, context_overrides)
    rules = load_catalog(dimensions=dimensions)
    findings = evaluate(signals, context, rules, run_id=run_id)

    if ai_rationale:
        from .ai import enrich_rationale

        findings = enrich_rationale(findings)

    return {"run_id": run_id, "context": context, "findings": findings}


def _safe(fn, default, errors, label):
    """Run a collector; on failure record the error and continue with a default."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - collectors must not abort the whole scan
        errors[label] = f"{type(exc).__name__}: {exc}"
        return default


def scan(
    token_provider,
    dimensions=None,
    context_overrides: dict = None,
    run_id: str = None,
    ai_rationale: bool = False,
    write: str = None,  # "json" | "lakehouse"
    table: str = "governance_findings",
    spark=None,
) -> dict:
    from .collectors import (
        AdminClient,
        collect_capacities,
        collect_domains,
        collect_pipelines,
        collect_tenant_settings,
        collect_workspaces,
    )

    client = AdminClient(token_provider)
    errors: dict = {}

    signals_dict = {
        "tenant_settings": _safe(lambda: collect_tenant_settings(client), {}, errors, "tenant_settings"),
        "capacities": _safe(lambda: collect_capacities(client), [], errors, "capacities"),
        "workspaces": _safe(lambda: collect_workspaces(client), [], errors, "workspaces"),
        "domains": _safe(lambda: collect_domains(client), [], errors, "domains"),
        "meta": {"pipelines": _safe(lambda: collect_pipelines(client), [], errors, "pipelines")},
    }
    if errors:
        signals_dict["meta"]["collection_errors"] = errors

    result = scan_from_signals(
        signals_dict,
        dimensions=dimensions,
        context_overrides=context_overrides,
        run_id=run_id,
        ai_rationale=ai_rationale,
    )
    result["signals"] = signals_dict
    if errors:
        result["collection_errors"] = errors

    if write == "json":
        from .writers import write_json

        result["output"] = write_json(result["findings"])
    elif write == "lakehouse":
        from .writers import write_lakehouse

        result["output"] = write_lakehouse(result["findings"], table=table, spark=spark)

    return result
