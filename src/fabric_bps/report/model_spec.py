"""Single source of truth for the governance report's measures.

Both deployment paths use these definitions:
  * the notebook auto-deploy path (`fabric_bps.report.deploy`) adds them via TOM, and
  * the shipped `.pbip` semantic model (powerbi/…/governance_findings.tmdl) mirrors them.

A test (tests/test_report_spec.py) asserts the two stay in sync so they can't drift.
"""
from __future__ import annotations

FACT_TABLE = "governance_findings"

# name -> DAX. Multi-line expressions are fine; whitespace is not significant.
MEASURES = [
    {
        "name": "Latest Run ID",
        "expression": (
            "VAR MaxTs = MAX ( governance_findings[timestamp] )\n"
            "RETURN\n"
            "    CALCULATE (\n"
            "        SELECTEDVALUE ( governance_findings[run_id] ),\n"
            "        FILTER ( ALL ( governance_findings ), governance_findings[timestamp] = MaxTs )\n"
            "    )"
        ),
        "format_string": None,
        "description": "run_id of the most recent scan (by timestamp); anchors the current-posture measures.",
    },
    {
        "name": "Findings (Latest Run)",
        "expression": "CALCULATE ( COUNTROWS ( governance_findings ), governance_findings[run_id] = [Latest Run ID] )",
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Adhered (Latest Run)",
        "expression": 'CALCULATE ( [Findings (Latest Run)], KEEPFILTERS ( governance_findings[status] = "adhered" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Gaps (Latest Run)",
        "expression": 'CALCULATE ( [Findings (Latest Run)], KEEPFILTERS ( governance_findings[status] = "gap" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Verify Applicability (Latest Run)",
        "expression": 'CALCULATE ( [Findings (Latest Run)], KEEPFILTERS ( governance_findings[status] = "verify-applicability" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Insufficient Data (Latest Run)",
        "expression": 'CALCULATE ( [Findings (Latest Run)], KEEPFILTERS ( governance_findings[status] = "insufficient-data" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Evaluated (Latest Run)",
        "expression": "[Adhered (Latest Run)] + [Gaps (Latest Run)]",
        "format_string": "0",
        "description": "Rules with a clear adhered/gap verdict this run (excludes verify/insufficient).",
    },
    {
        "name": "Adherence Rate (Latest Run)",
        "expression": "DIVIDE ( [Adhered (Latest Run)], [Evaluated (Latest Run)] )",
        "format_string": "0.0%",
        "description": "Share of clearly evaluated rules that are adhered (adhered / (adhered + gaps)).",
    },
    {
        "name": "High-Impact Gaps (Latest Run)",
        "expression": 'CALCULATE ( [Gaps (Latest Run)], KEEPFILTERS ( governance_findings[impact] = "high" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Adhered (This Run)",
        "expression": 'CALCULATE ( COUNTROWS ( governance_findings ), KEEPFILTERS ( governance_findings[status] = "adhered" ) )',
        "format_string": "0",
        "description": "Respects run_id/timestamp on the axis; use for trend visuals.",
    },
    {
        "name": "Gaps (This Run)",
        "expression": 'CALCULATE ( COUNTROWS ( governance_findings ), KEEPFILTERS ( governance_findings[status] = "gap" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Adherence Rate (This Run)",
        "expression": "DIVIDE ( [Adhered (This Run)], [Adhered (This Run)] + [Gaps (This Run)] )",
        "format_string": "0.0%",
        "description": None,
    },
]

MEASURE_NAMES = [m["name"] for m in MEASURES]
