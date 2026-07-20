"""Build a populated Power BI report layout (classic report.json) for the findings model.

Produces a two-page report bound to the ``governance_findings`` table and its measures:
  * Governance Overview  — KPI cards + charts by area / status / severity / impact.
  * Findings Detail      — a status slicer + a findings table.

``deploy_report`` deploys the output via ``sempy_labs.report.create_report_from_reportjson``,
and the shipped ``.pbip`` report mirrors it. Kept as a builder (not static JSON) so the
visuals stay in sync with the fact table in one place.
"""
from __future__ import annotations

import json

from .model_spec import FACT_TABLE

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


def _card(name, measure, x, y, w, h, z, table):
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


def build_report_json(table: str = FACT_TABLE) -> dict:
    count = "Findings (Latest Run)"

    overview = [
        _card("cardFindings", count, 16, 16, 296, 92, 1, table),
        _card("cardGaps", "Gaps (Latest Run)", 324, 16, 296, 92, 2, table),
        _card("cardHighGaps", "High-Impact Gaps (Latest Run)", 632, 16, 296, 92, 3, table),
        _card("cardAdherence", "Adherence Rate (Latest Run)", 940, 16, 296, 92, 4, table),
        _cat_value("barArea", "clusteredBarChart", "dimension", count, 16, 120, 616, 290, 5, table, "Findings by area"),
        _cat_value("donutStatus", "donutChart", "status", count, 648, 120, 616, 290, 6, table, "Findings by status"),
        _cat_value("colSeverity", "clusteredColumnChart", "severity", count, 16, 422, 616, 282, 7, table, "Findings by severity"),
        _cat_value("colImpact", "clusteredColumnChart", "impact", "Gaps (Latest Run)", 648, 422, 616, 282, 8, table, "Gaps by impact"),
    ]

    table_cols = ["dimension", "title", "status", "severity", "recommendation"]
    detail = [
        _container(
            "slicerStatus",
            "slicer",
            16,
            16,
            250,
            400,
            1,
            {"Values": [{"queryRef": f"{table}.status"}]},
            [_column_select("status", table)],
            table,
        ),
        _container(
            "tableFindings",
            "tableEx",
            282,
            16,
            982,
            688,
            2,
            {"Values": [{"queryRef": f"{table}.{c}"} for c in table_cols]},
            [_column_select(c, table) for c in table_cols],
            table,
            title="Findings",
        ),
    ]

    report_config = {
        "version": "5.55",
        "themeCollection": {"baseTheme": {"name": "CY24SU10"}},
        "activeSectionIndex": 0,
        "defaultDrillFilterOtherVisuals": True,
        "settings": {"useStylableVisualContainerHeader": True},
    }

    def page(name, display, ordinal, visuals):
        return {
            "name": name,
            "displayName": display,
            "filters": "[]",
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
        ],
    }
