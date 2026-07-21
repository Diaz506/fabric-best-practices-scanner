"""Validate the generated report layout: valid JSON and only real measures/columns.

Guards against a visual silently referencing a measure or column that does not exist
in the semantic model (which would break the report on deploy).
"""
import json

from fabric_bps.report import (
    FACT_TABLE,
    INVENTORY_MEASURE_NAMES,
    INVENTORY_TABLE,
    MEASURE_NAMES,
    build_report_json,
)

# Columns of the governance_findings fact table (from Finding.to_row()).
COLUMNS = {
    "run_id", "timestamp", "rule_id", "dimension", "title", "waf_pillar", "status",
    "impact", "severity", "applicability_confidence", "recommendation", "rationale",
    "references", "reference_url", "effort", "evidence", "archetype",
}

# Columns of the governance_inventory table (from InventoryItem.to_row()).
INVENTORY_COLUMNS = {
    "run_id", "timestamp", "resource_type", "resource_id", "name", "state", "sku",
    "region", "on_dedicated_capacity", "capacity_name", "domain_name", "admin_count",
    "user_count", "is_orphan", "orphan_reasons",
}

_COLUMNS_BY_TABLE = {FACT_TABLE: COLUMNS, INVENTORY_TABLE: INVENTORY_COLUMNS}
_MEASURES_BY_TABLE = {
    FACT_TABLE: set(MEASURE_NAMES),
    INVENTORY_TABLE: set(INVENTORY_MEASURE_NAMES),
}


def _visuals(rj):
    for section in rj["sections"]:
        for vc in section["visualContainers"]:
            yield section, vc


def test_report_json_shape():
    rj = build_report_json()
    assert len(rj["sections"]) == 4
    json.loads(rj["config"])  # report config is a valid JSON string
    for section in rj["sections"]:
        assert list(section["visualContainers"])  # every page has visuals


def test_every_visual_binds_to_real_fields():
    all_measures = set(MEASURE_NAMES) | set(INVENTORY_MEASURE_NAMES)
    all_columns = COLUMNS | INVENTORY_COLUMNS
    rj = build_report_json()
    seen = 0
    for _, vc in _visuals(rj):
        config = json.loads(vc["config"])  # each visual config is valid JSON
        entity = config["singleVisual"]["prototypeQuery"]["From"][0]["Entity"]
        measures = _MEASURES_BY_TABLE.get(entity, all_measures)
        columns = _COLUMNS_BY_TABLE.get(entity, all_columns)
        for sel in config["singleVisual"]["prototypeQuery"]["Select"]:
            if "Measure" in sel:
                assert sel["Measure"]["Property"] in measures, sel
            else:
                assert sel["Column"]["Property"] in columns, sel
        seen += 1
    assert seen >= 8


def test_visual_names_unique():
    rj = build_report_json()
    names = [json.loads(vc["config"])["name"] for _, vc in _visuals(rj)]
    assert len(names) == len(set(names))


def test_orphans_page_hard_filtered_to_orphans():
    rj = build_report_json()
    pages = {s["name"]: s for s in rj["sections"]}
    for s in rj["sections"]:
        json.loads(s["filters"])  # every page's filters is valid JSON
    orphans = pages["page-orphans"]
    filters = json.loads(orphans["filters"])
    assert filters, "Orphans page must carry a page-level filter"
    f = filters[0]
    assert f["expression"]["Column"]["Property"] == "is_orphan"
    values = f["filter"]["Where"][0]["Condition"]["In"]["Values"]
    assert values == [[{"Literal": {"Value": "'Yes'"}}]]
    # the confusing is_orphan slicer is gone now that the page is pre-filtered
    names = [json.loads(vc["config"])["name"] for vc in orphans["visualContainers"]]
    assert "slicerOrphanFlag" not in names
