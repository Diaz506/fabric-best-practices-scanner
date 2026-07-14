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
    from .collectors import AdminClient, collect_capacities, collect_tenant_settings

    client = AdminClient(token_provider)
    signals_dict = {
        "tenant_settings": collect_tenant_settings(client),
        "capacities": collect_capacities(client),
    }

    result = scan_from_signals(
        signals_dict,
        dimensions=dimensions,
        context_overrides=context_overrides,
        run_id=run_id,
        ai_rationale=ai_rationale,
    )
    result["signals"] = signals_dict

    if write == "json":
        from .writers import write_json

        result["output"] = write_json(result["findings"])
    elif write == "lakehouse":
        from .writers import write_lakehouse

        result["output"] = write_lakehouse(result["findings"], table=table, spark=spark)

    return result
