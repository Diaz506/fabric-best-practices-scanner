"""Auto-deploy the DirectLake semantic model (and optionally a report) into Fabric.

Runs inside a Fabric notebook after the scan has written the ``governance_findings``
Delta table. It creates a Direct Lake semantic model bound to the *live* Lakehouse (so
there are no connection placeholders to fill in) and adds the governance measures from
``model_spec``. This drops the manual deployment effort to just: run ``00_deploy.py``
(which provisions the Lakehouse) — or attach a Lakehouse and run ``01_run_scanner.py``.

Requires ``semantic-link-labs`` (present in the Fabric runtime; ``pip install
'fabric-best-practices-scanner[deploy]'`` elsewhere).
"""
from __future__ import annotations

from .model_spec import FACT_TABLE, MEASURES


def _resolve_source(lakehouse):
    if lakehouse is not None:
        return lakehouse
    import sempy.fabric as fabric

    return fabric.get_lakehouse_id()  # the Lakehouse attached to this notebook


def deploy_semantic_model(
    dataset: str = "FabricGovernance",
    lakehouse=None,
    workspace=None,
    table: str = FACT_TABLE,
    use_sql_endpoint: bool = False,
    refresh: bool = True,
) -> str:
    """Create/refresh the Direct Lake model and (idempotently) add the measures.

    Parameters mirror semantic-link-labs. ``lakehouse``/``workspace`` default to the
    notebook's attached Lakehouse and workspace. Returns the dataset name.
    """
    from sempy_labs.directlake import generate_direct_lake_semantic_model
    from sempy_labs.tom import connect_semantic_model

    source = _resolve_source(lakehouse)

    generate_direct_lake_semantic_model(
        dataset=dataset,
        tables=[table],
        source=source,
        source_type="Lakehouse",
        use_sql_endpoint=use_sql_endpoint,
        workspace=workspace,
        refresh=refresh,
    )

    with connect_semantic_model(dataset=dataset, workspace=workspace, readonly=False) as tom:
        existing = {m.Name for t in tom.model.Tables for m in t.Measures}
        for m in MEASURES:
            if m["name"] in existing:
                continue
            tom.add_measure(
                table_name=table,
                measure_name=m["name"],
                expression=m["expression"],
                format_string=m.get("format_string"),
                description=m.get("description"),
            )

    return dataset


def deploy_report(
    dataset: str = "FabricGovernance",
    report: str = "FabricGovernance",
    workspace: str = None,
) -> str:
    """Optional: create a bound (starter) report on the model.

    Non-fatal: if report creation is unavailable, the shipped `.pbip` report can be used
    instead. Returns the report name (or an explanatory message).
    """
    starter = {
        "config": '{"version":"5.55","themeCollection":{"baseTheme":{"name":"CY24SU10"}},"activeSectionIndex":0,"settings":{"useStylableVisualContainerHeader":true}}',
        "layoutOptimization": 0,
        "publicCustomVisuals": [],
        "resourcePackages": [],
        "sections": [
            {
                "name": "page-overview",
                "displayName": "Governance Overview",
                "filters": "[]",
                "ordinal": 0,
                "visualContainers": [],
                "config": "{}",
                "displayOption": 1,
                "width": 1280,
                "height": 720,
            },
            {
                "name": "page-detail",
                "displayName": "Findings Detail",
                "filters": "[]",
                "ordinal": 1,
                "visualContainers": [],
                "config": "{}",
                "displayOption": 1,
                "width": 1280,
                "height": 720,
            },
        ],
    }
    try:
        from sempy_labs.report import create_report_from_reportjson

        create_report_from_reportjson(
            report=report,
            dataset=dataset,
            report_json=starter,
            workspace=workspace,
        )
        return report
    except Exception as exc:  # noqa: BLE001 - report deploy is optional
        return f"report not created ({type(exc).__name__}: {exc}); use the shipped .pbip report instead"
