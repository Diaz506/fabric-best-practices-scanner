"""Validate the generated report layout: valid JSON and only real measures/columns.

Guards against a visual silently referencing a measure or column that does not exist
in the semantic model (which would break the report on deploy).
"""
import json

from fabric_bps.report import MEASURE_NAMES, build_report_json

# Columns of the governance_findings fact table (from Finding.to_row()).
COLUMNS = {
    "run_id", "timestamp", "rule_id", "dimension", "title", "waf_pillar", "status",
    "impact", "severity", "applicability_confidence", "recommendation", "rationale",
    "references", "reference_url", "effort", "evidence", "archetype",
}


def _visuals(rj):
    for section in rj["sections"]:
        for vc in section["visualContainers"]:
            yield section, vc


def test_report_json_shape():
    rj = build_report_json()
    assert len(rj["sections"]) == 2
    json.loads(rj["config"])  # report config is a valid JSON string
    assert list(rj["sections"][0]["visualContainers"])  # overview has visuals
    assert list(rj["sections"][1]["visualContainers"])  # detail has visuals


def test_every_visual_binds_to_real_fields():
    measures = set(MEASURE_NAMES)
    rj = build_report_json()
    seen = 0
    for _, vc in _visuals(rj):
        config = json.loads(vc["config"])  # each visual config is valid JSON
        for sel in config["singleVisual"]["prototypeQuery"]["Select"]:
            if "Measure" in sel:
                assert sel["Measure"]["Property"] in measures, sel
            else:
                assert sel["Column"]["Property"] in COLUMNS, sel
        seen += 1
    assert seen >= 8


def test_visual_names_unique():
    rj = build_report_json()
    names = [json.loads(vc["config"])["name"] for _, vc in _visuals(rj)]
    assert len(names) == len(set(names))
