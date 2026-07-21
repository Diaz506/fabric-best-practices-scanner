"""Auto-deploy the DirectLake semantic model (and optionally a report) into Fabric.

Runs inside a Fabric notebook after the scan has written the ``governance_findings``
Delta table. It creates a Direct Lake semantic model bound to the *live* Lakehouse (so
there are no connection placeholders to fill in) and adds the governance measures from
``model_spec``. This drops the manual deployment effort to just: run ``00_deploy.ipynb``
(which provisions the Lakehouse) — or attach a Lakehouse and run ``01_run_scanner.py``.

Requires ``semantic-link-labs`` (not preinstalled in the Fabric runtime; install via
the package's ``[deploy]`` extra, e.g. ``pip install
'fabric-best-practices-scanner[deploy]'``).
"""
from __future__ import annotations

from .model_spec import (
    FACT_TABLE,
    INVENTORY_MEASURES,
    INVENTORY_TABLE,
    MEASURES,
)


def _resolve_source(lakehouse):
    if lakehouse is not None:
        return lakehouse
    import sempy.fabric as fabric

    return fabric.get_lakehouse_id()  # the Lakehouse attached to this notebook


def _categorize_url_columns(tom, table: str) -> None:
    """Mark the reference_url column as a Web URL so the report renders it as a link."""
    for t in tom.model.Tables:
        if t.Name != table:
            continue
        for col in t.Columns:
            if col.Name == "reference_url":
                try:
                    col.DataCategory = "WebUrl"
                except Exception:  # noqa: BLE001 - categorization is best-effort
                    pass


def _sync_measures(tom, table: str, measures: list, existing: dict) -> None:
    """Add missing measures and keep existing ones in sync with the spec (self-healing)."""
    for m in measures:
        fmt = m.get("format_string")
        desc = m.get("description")
        if m["name"] in existing:
            meas = existing[m["name"]]
            meas.Expression = m["expression"]
            if fmt is not None:
                meas.FormatString = fmt
            if desc is not None:
                meas.Description = desc
            continue
        tom.add_measure(
            table_name=table,
            measure_name=m["name"],
            expression=m["expression"],
            format_string=fmt,
            description=desc,
        )


def deploy_semantic_model(
    dataset: str = "FabricGovernance",
    lakehouse=None,
    workspace=None,
    table: str = FACT_TABLE,
    inventory_table: str = INVENTORY_TABLE,
    include_inventory: bool = True,
    use_sql_endpoint: bool = False,
    refresh: bool = True,
) -> str:
    """Create/refresh the Direct Lake model and (idempotently) add the measures.

    Parameters mirror semantic-link-labs. ``lakehouse``/``workspace`` default to the
    notebook's attached Lakehouse and workspace. When ``include_inventory`` is set and the
    ``governance_inventory`` table exists in the Lakehouse, it is added to the model with
    its own control-center measures. Returns the dataset name.
    """
    from sempy_labs.directlake import generate_direct_lake_semantic_model
    from sempy_labs.tom import connect_semantic_model

    source = _resolve_source(lakehouse)

    tables = [table]
    if include_inventory:
        tables.append(inventory_table)

    try:
        generate_direct_lake_semantic_model(
            dataset=dataset,
            tables=tables,
            source=source,
            source_type="Lakehouse",
            use_sql_endpoint=use_sql_endpoint,
            workspace=workspace,
            refresh=refresh,
        )
    except Exception:  # noqa: BLE001 - inventory table may not exist yet; fall back to findings only
        if include_inventory:
            generate_direct_lake_semantic_model(
                dataset=dataset,
                tables=[table],
                source=source,
                source_type="Lakehouse",
                use_sql_endpoint=use_sql_endpoint,
                workspace=workspace,
                refresh=refresh,
            )
        else:
            raise

    with connect_semantic_model(dataset=dataset, workspace=workspace, readonly=False) as tom:
        _categorize_url_columns(tom, table)
        model_tables = {t.Name for t in tom.model.Tables}
        existing = {m.Name: m for t in tom.model.Tables for m in t.Measures}
        _sync_measures(tom, table, MEASURES, existing)
        if inventory_table in model_tables:
            _sync_measures(tom, inventory_table, INVENTORY_MEASURES, existing)

    return dataset


def deploy_report(
    dataset: str = "FabricGovernance",
    report: str = "FabricGovernance",
    workspace: str = None,
) -> str:
    """Create a populated report (cards + charts + table) bound to the model.

    Non-fatal: if report creation is unavailable, the shipped `.pbip` report can be used
    instead. Returns the report name (or an explanatory message).
    """
    from .report_layout import build_report_json

    report_json = build_report_json()
    try:
        from sempy_labs.report import create_report_from_reportjson

        create_report_from_reportjson(
            report=report,
            dataset=dataset,
            report_json=report_json,
            workspace=workspace,
        )
        return report
    except Exception as exc:  # noqa: BLE001 - report deploy is optional
        return f"report not created ({type(exc).__name__}: {exc}); use the shipped .pbip report instead"
