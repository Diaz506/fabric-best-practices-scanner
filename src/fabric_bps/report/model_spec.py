"""Single source of truth for the governance report's columns and measures.

Both deployment paths use these definitions:
  * the notebook auto-deploy path (`fabric_bps.report.deploy`) adds them via TOM, and
  * the shipped `.pbip` semantic model (powerbi/…/governance_findings.tmdl) mirrors them.

Tests (tests/test_report_spec.py) assert the two stay in sync so they can't drift.

Columns are stored in the Lakehouse Delta tables with snake_case names (the ``source``);
the semantic model renames them to friendly display names (the ``name``) so report headers,
slicers, and axes read cleanly. Measures and the report layout reference the friendly names.
"""
from __future__ import annotations

FACT_TABLE = "governance_findings"

# Friendly display columns for the findings fact table.
# ``source`` is the snake_case Delta column; ``name`` is the friendly model column.
FACT_COLUMNS = [
    {"source": "run_id", "name": "Run ID", "data_type": "string"},
    {"source": "timestamp", "name": "Timestamp", "data_type": "string"},
    {"source": "rule_id", "name": "Rule ID", "data_type": "string"},
    {"source": "dimension", "name": "Area", "data_type": "string"},
    {"source": "title", "name": "Best practice", "data_type": "string"},
    {"source": "waf_pillar", "name": "WAF pillar", "data_type": "string"},
    {"source": "status", "name": "Status", "data_type": "string"},
    {"source": "impact", "name": "Impact", "data_type": "string"},
    {"source": "severity", "name": "Severity", "data_type": "string"},
    {"source": "applicability_confidence", "name": "Applicability %", "data_type": "int64", "format_string": "0"},
    {"source": "recommendation", "name": "Recommendation", "data_type": "string"},
    {"source": "rationale", "name": "Rationale", "data_type": "string"},
    {"source": "references", "name": "References", "data_type": "string"},
    {"source": "reference_url", "name": "Docs", "data_type": "string", "category": "WebUrl"},
    {"source": "effort", "name": "Effort", "data_type": "string"},
    {"source": "evidence", "name": "Evidence", "data_type": "string"},
    {"source": "archetype", "name": "Archetype", "data_type": "string"},
]

FACT_COLUMN_NAMES = [c["name"] for c in FACT_COLUMNS]

# name -> DAX. Multi-line expressions are fine; whitespace is not significant.
MEASURES = [
    {
        "name": "Latest Run ID",
        "expression": (
            "VAR MaxTs = MAX ( governance_findings[Timestamp] )\n"
            "RETURN\n"
            "    CALCULATE (\n"
            "        SELECTEDVALUE ( governance_findings[Run ID] ),\n"
            "        FILTER ( ALL ( governance_findings ), governance_findings[Timestamp] = MaxTs )\n"
            "    )"
        ),
        "format_string": None,
        "description": "run_id of the most recent scan (by timestamp); anchors the current-posture measures.",
    },
    {
        "name": "Findings (Latest Run)",
        "expression": (
            "VAR lr = [Latest Run ID]\n"
            "RETURN\n"
            "    CALCULATE ( COUNTROWS ( governance_findings ), governance_findings[Run ID] = lr )"
        ),
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Adhered (Latest Run)",
        "expression": 'CALCULATE ( [Findings (Latest Run)], KEEPFILTERS ( governance_findings[Status] = "adhered" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Gaps (Latest Run)",
        "expression": 'CALCULATE ( [Findings (Latest Run)], KEEPFILTERS ( governance_findings[Status] = "gap" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Verify Applicability (Latest Run)",
        "expression": 'CALCULATE ( [Findings (Latest Run)], KEEPFILTERS ( governance_findings[Status] = "verify-applicability" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Insufficient Data (Latest Run)",
        "expression": 'CALCULATE ( [Findings (Latest Run)], KEEPFILTERS ( governance_findings[Status] = "insufficient-data" ) )',
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
        "expression": 'CALCULATE ( [Gaps (Latest Run)], KEEPFILTERS ( governance_findings[Impact] = "high" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Adhered (This Run)",
        "expression": 'CALCULATE ( COUNTROWS ( governance_findings ), KEEPFILTERS ( governance_findings[Status] = "adhered" ) )',
        "format_string": "0",
        "description": "Respects run_id/timestamp on the axis; use for trend visuals.",
    },
    {
        "name": "Gaps (This Run)",
        "expression": 'CALCULATE ( COUNTROWS ( governance_findings ), KEEPFILTERS ( governance_findings[Status] = "gap" ) )',
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

# --- Inventory (admin control center) ---------------------------------------
INVENTORY_TABLE = "governance_inventory"

INVENTORY_COLUMNS = [
    {"source": "run_id", "name": "Run ID", "data_type": "string"},
    {"source": "timestamp", "name": "Timestamp", "data_type": "string"},
    {"source": "resource_type", "name": "Resource type", "data_type": "string"},
    {"source": "resource_id", "name": "Resource ID", "data_type": "string"},
    {"source": "name", "name": "Name", "data_type": "string"},
    {"source": "state", "name": "State", "data_type": "string"},
    {"source": "sku", "name": "SKU", "data_type": "string"},
    {"source": "region", "name": "Region", "data_type": "string"},
    {"source": "on_dedicated_capacity", "name": "On dedicated capacity", "data_type": "string"},
    {"source": "capacity_name", "name": "Capacity", "data_type": "string"},
    {"source": "domain_name", "name": "Domain", "data_type": "string"},
    {"source": "admin_count", "name": "Admins", "data_type": "int64", "format_string": "0"},
    {"source": "user_count", "name": "Users", "data_type": "int64", "format_string": "0"},
    {"source": "is_orphan", "name": "Orphaned", "data_type": "string"},
    {"source": "orphan_reasons", "name": "Why flagged", "data_type": "string"},
]

INVENTORY_COLUMN_NAMES = [c["name"] for c in INVENTORY_COLUMNS]

INVENTORY_MEASURES = [
    {
        "name": "Latest Inventory Run ID",
        "expression": (
            "VAR MaxTs = MAX ( governance_inventory[Timestamp] )\n"
            "RETURN\n"
            "    CALCULATE (\n"
            "        SELECTEDVALUE ( governance_inventory[Run ID] ),\n"
            "        FILTER ( ALL ( governance_inventory ), governance_inventory[Timestamp] = MaxTs )\n"
            "    )"
        ),
        "format_string": None,
        "description": "run_id of the most recent inventory snapshot; anchors the current-state counts.",
    },
    {
        "name": "Resources (Latest Run)",
        "expression": (
            "VAR lr = [Latest Inventory Run ID]\n"
            "RETURN\n"
            "    CALCULATE ( COUNTROWS ( governance_inventory ), governance_inventory[Run ID] = lr )"
        ),
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Orphaned Resources (Latest Run)",
        "expression": 'CALCULATE ( [Resources (Latest Run)], KEEPFILTERS ( governance_inventory[Orphaned] = "Yes" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Workspaces (Latest Run)",
        "expression": 'CALCULATE ( [Resources (Latest Run)], KEEPFILTERS ( governance_inventory[Resource type] = "Workspace" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Capacities (Latest Run)",
        "expression": 'CALCULATE ( [Resources (Latest Run)], KEEPFILTERS ( governance_inventory[Resource type] = "Capacity" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Domains (Latest Run)",
        "expression": 'CALCULATE ( [Resources (Latest Run)], KEEPFILTERS ( governance_inventory[Resource type] = "Domain" ) )',
        "format_string": "0",
        "description": None,
    },
    {
        "name": "Capacities Without Workspaces (Latest Run)",
        "expression": (
            "VAR lr = [Latest Inventory Run ID]\n"
            "RETURN\n"
            "    CALCULATE (\n"
            "        COUNTROWS ( governance_inventory ),\n"
            "        governance_inventory[Run ID] = lr,\n"
            '        governance_inventory[Resource type] = "Capacity",\n'
            '        CONTAINSSTRING ( governance_inventory[Why flagged], "no-workspaces-assigned" )\n'
            "    )"
        ),
        "format_string": "0",
        "description": "Capacities in the latest snapshot with no workspaces assigned (candidates to pause or remove).",
    },
]

INVENTORY_MEASURE_NAMES = [m["name"] for m in INVENTORY_MEASURES]
