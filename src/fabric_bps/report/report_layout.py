"""Build a populated Power BI report layout (classic report.json) for the findings model.

Produces a four-page report bound to the ``governance_findings`` fact table and the
``governance_inventory`` inventory table (admin control center):
  * Governance Overview  — KPI cards + charts by area / status / severity / impact.
  * Findings Detail      — area + status slicers + a findings table with doc links.
  * Resource Inventory   — resource counts + a type x state matrix + a resource table.
  * Orphans & Unused     — slicers + a table of orphaned/unused resources and why.

``deploy_report`` deploys the output via ``sempy_labs.report.create_report_from_reportjson``,
and the shipped ``.pbip`` report mirrors it. Kept as a builder (not static JSON) so the
visuals stay in sync with the fact table in one place.
"""
from __future__ import annotations

import json

from .model_spec import FACT_TABLE, INVENTORY_TABLE

_SRC = "g"


def _measure_select(prop: str, table: str):
    return {
        "Measure": {"Expression": {"SourceRef": {"Source": _SRC}}, "Property": prop},
        "Name": f"{table}.{prop}",
    }


def _column_select(prop: str, table: str):
    return {
        "Column": {"Expression": {"SourceRef": {"Source": _SRC}}, "Property": prop},
        "Name": f"{table}.{prop}",
    }


def _prototype(selects, table: str):
    return {
        "Version": 2,
        "From": [{"Name": _SRC, "Entity": table, "Type": 0}],
        "Select": selects,
    }


def _categorical_eq_filter(fname, column, value, table):
    """Classic report.json categorical equality filter (e.g. is_orphan = 'Yes')."""
    return {
        "name": fname,
        "expression": {
            "Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}
        },
        "filter": {
            "Version": 2,
            "From": [{"Name": _SRC, "Entity": table, "Type": 0}],
            "Where": [
                {
                    "Condition": {
                        "In": {
                            "Expressions": [
                                {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Source": _SRC}},
                                        "Property": column,
                                    }
                                }
                            ],
                            "Values": [[{"Literal": {"Value": f"'{value}'"}}]],
                        }
                    }
                }
            ],
        },
        "type": "Categorical",
    }


def _container(name, vtype, x, y, w, h, z, projections, selects, table, title=None):
    single = {
        "visualType": vtype,
        "projections": projections,
        "prototypeQuery": _prototype(selects, table),
        "drillFilterOtherVisuals": True,
    }
    if title:
        single["vcObjects"] = {
            "title": [
                {
                    "properties": {
                        "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                    }
                }
            ]
        }
    config = {
        "name": name,
        "layouts": [
            {"id": 0, "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z}}
        ],
        "singleVisual": single,
    }
    return {
        "x": x,
        "y": y,
        "z": z,
        "width": w,
        "height": h,
        "config": json.dumps(config),
        "filters": "[]",
    }


def _card(name, measure, x, y, w, h, z, table, title=None):
    return _container(
        name,
        "card",
        x,
        y,
        w,
        h,
        z,
        {"Values": [{"queryRef": f"{table}.{measure}"}]},
        [_measure_select(measure, table)],
        table,
        title=title,
    )


def _matrix(name, rows, cols, measure, x, y, w, h, z, table, title):
    return _container(
        name,
        "pivotTable",
        x,
        y,
        w,
        h,
        z,
        {
            "Rows": [{"queryRef": f"{table}.{rows}"}],
            "Columns": [{"queryRef": f"{table}.{cols}"}],
            "Values": [{"queryRef": f"{table}.{measure}"}],
        },
        [_column_select(rows, table), _column_select(cols, table), _measure_select(measure, table)],
        table,
        title=title,
    )


def _slicer(name, column, x, y, w, h, z, table, title):
    return _container(
        name,
        "slicer",
        x,
        y,
        w,
        h,
        z,
        {"Values": [{"queryRef": f"{table}.{column}"}]},
        [_column_select(column, table)],
        table,
        title=title,
    )


def _cat_value(name, vtype, category, measure, x, y, w, h, z, table, title):
    return _container(
        name,
        vtype,
        x,
        y,
        w,
        h,
        z,
        {
            "Category": [{"queryRef": f"{table}.{category}"}],
            "Y": [{"queryRef": f"{table}.{measure}"}],
        },
        [_column_select(category, table), _measure_select(measure, table)],
        table,
        title=title,
    )


def build_report_json(table: str = FACT_TABLE, inventory_table: str = INVENTORY_TABLE) -> dict:
    count = "Findings (Latest Run)"

    # Page 1 — Governance Overview: labeled KPIs, a categorized area x status matrix,
    # and supporting charts.
    overview = [
        _card("cardFindings", count, 16, 16, 296, 96, 1, table, title="Findings (latest run)"),
        _card("cardGaps", "Gaps (Latest Run)", 324, 16, 296, 96, 2, table, title="Gaps"),
        _card("cardHighGaps", "High-Impact Gaps (Latest Run)", 632, 16, 296, 96, 3, table, title="High-impact gaps"),
        _card("cardAdherence", "Adherence Rate (Latest Run)", 940, 16, 296, 96, 4, table, title="Adherence rate"),
        _matrix(
            "matrixAreaStatus", "dimension", "status", count,
            16, 124, 760, 300, 5, table, "Findings by area and status",
        ),
        _cat_value("donutStatus", "donutChart", "status", count, 792, 124, 472, 300, 6, table, "Findings by status"),
        _cat_value("colSeverity", "clusteredColumnChart", "severity", count, 16, 436, 616, 268, 7, table, "Findings by severity"),
        _cat_value("colImpact", "clusteredColumnChart", "impact", "Gaps (Latest Run)", 648, 436, 616, 268, 8, table, "Gaps by impact"),
    ]

    # Page 2 — Findings Detail: filter by area/status, read the finding + recommendation,
    # and open the official documentation via the clickable link column.
    table_cols = ["dimension", "title", "status", "impact", "severity", "effort", "recommendation", "reference_url"]
    detail = [
        _slicer("slicerArea", "dimension", 16, 16, 250, 336, 1, table, "Area"),
        _slicer("slicerStatus", "status", 16, 360, 250, 344, 2, table, "Status"),
        _container(
            "tableFindings",
            "tableEx",
            282,
            16,
            982,
            688,
            3,
            {"Values": [{"queryRef": f"{table}.{c}"} for c in table_cols]},
            [_column_select(c, table) for c in table_cols],
            table,
            title="Findings & recommendations (open the link for official guidance)",
        ),
    ]

    # Page 3 — Resource Inventory (admin control center): current-state counts of every
    # workspace, capacity, and domain, with a resource_type x state breakdown and a browsable
    # resource table.
    inv_count = "Resources (Latest Run)"
    inv_cols = [
        "resource_type", "name", "state", "sku", "region",
        "capacity_name", "domain_name", "admin_count", "user_count", "is_orphan",
    ]
    inventory = [
        _card("cardResources", inv_count, 16, 16, 240, 96, 1, inventory_table, title="Resources (latest run)"),
        _card("cardWorkspaces", "Workspaces (Latest Run)", 264, 16, 240, 96, 2, inventory_table, title="Workspaces"),
        _card("cardCapacities", "Capacities (Latest Run)", 512, 16, 240, 96, 3, inventory_table, title="Capacities"),
        _card("cardDomains", "Domains (Latest Run)", 760, 16, 240, 96, 4, inventory_table, title="Domains"),
        _card("cardOrphaned", "Orphaned Resources (Latest Run)", 1008, 16, 256, 96, 5, inventory_table, title="Orphaned"),
        _matrix(
            "matrixTypeState", "resource_type", "state", inv_count,
            16, 124, 500, 300, 6, inventory_table, "Resources by type and state",
        ),
        _slicer("slicerInvType", "resource_type", 532, 124, 250, 300, 7, inventory_table, "Resource type"),
        _container(
            "tableInventory",
            "tableEx",
            16,
            436,
            1248,
            268,
            8,
            {"Values": [{"queryRef": f"{inventory_table}.{c}"} for c in inv_cols]},
            [_column_select(c, inventory_table) for c in inv_cols],
            inventory_table,
            title="Resource inventory",
        ),
    ]

    # Page 4 — Orphans & Unused: slicers to focus on orphaned/unused resources and the
    # reasons they were flagged, so admins can clean up or reassign.
    # Page 4 — Orphans & Unused: hard-filtered to orphaned/unused resources so the page shows
    # only what needs cleanup (no need to toggle a slicer). Resource-type slicer to focus by kind.
    orphan_cols = [
        "name", "resource_type", "state", "orphan_reasons",
        "capacity_name", "domain_name", "admin_count", "user_count",
    ]
    orphans = [
        _card("cardOrphanTotal", "Orphaned Resources (Latest Run)", 16, 16, 296, 96, 1, inventory_table, title="Orphaned resources"),
        _slicer("slicerOrphanType", "resource_type", 16, 124, 250, 580, 2, inventory_table, "Resource type"),
        _container(
            "tableOrphans",
            "tableEx",
            282,
            124,
            982,
            580,
            3,
            {"Values": [{"queryRef": f"{inventory_table}.{c}"} for c in orphan_cols]},
            [_column_select(c, inventory_table) for c in orphan_cols],
            inventory_table,
            title="Orphaned & unused resources — what to clean up or reassign",
        ),
    ]
    orphans_filters = json.dumps(
        [_categorical_eq_filter("orphanOnly", "is_orphan", "Yes", inventory_table)]
    )

    report_config = {
        "version": "5.55",
        "themeCollection": {"baseTheme": {"name": "CY24SU10"}},
        "activeSectionIndex": 0,
        "defaultDrillFilterOtherVisuals": True,
        "settings": {"useStylableVisualContainerHeader": True},
    }

    def page(name, display, ordinal, visuals, filters="[]"):
        return {
            "name": name,
            "displayName": display,
            "filters": filters,
            "ordinal": ordinal,
            "visualContainers": visuals,
            "config": "{}",
            "displayOption": 1,
            "width": 1280,
            "height": 720,
        }

    return {
        "config": json.dumps(report_config),
        "layoutOptimization": 0,
        "publicCustomVisuals": [],
        "resourcePackages": [],
        "sections": [
            page("page-overview", "Governance Overview", 0, overview),
            page("page-detail", "Findings Detail", 1, detail),
            page("page-inventory", "Resource Inventory", 2, inventory),
            page("page-orphans", "Orphans & Unused", 3, orphans, filters=orphans_filters),
        ],
    }
