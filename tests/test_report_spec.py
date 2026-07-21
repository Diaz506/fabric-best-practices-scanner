import os
import re

from fabric_bps.report import (
    FACT_COLUMNS,
    FACT_COLUMN_NAMES,
    INVENTORY_COLUMNS,
    INVENTORY_COLUMN_NAMES,
    INVENTORY_MEASURE_NAMES,
    INVENTORY_MEASURES,
    MEASURE_NAMES,
    MEASURES,
)

HERE = os.path.dirname(__file__)
TMDL = os.path.join(
    HERE,
    "..",
    "powerbi",
    "FabricGovernance.SemanticModel",
    "definition",
    "tables",
    "governance_findings.tmdl",
)
INVENTORY_TMDL = os.path.join(
    HERE,
    "..",
    "powerbi",
    "FabricGovernance.SemanticModel",
    "definition",
    "tables",
    "governance_inventory.tmdl",
)


def test_measure_names_unique_and_nonempty():
    assert len(MEASURE_NAMES) == len(set(MEASURE_NAMES))
    for m in MEASURES:
        assert m["name"].strip()
        assert m["expression"].strip()


def test_spec_matches_shipped_tmdl():
    """The notebook deploy path and the .pbip model must expose the same measures."""
    with open(TMDL, encoding="utf-8") as f:
        text = f.read()
    tmdl_names = set(re.findall(r"measure\s+'([^']+)'\s*=", text))
    assert set(MEASURE_NAMES) == tmdl_names, (
        f"Drift between model_spec and TMDL. "
        f"Only in spec: {set(MEASURE_NAMES) - tmdl_names}. "
        f"Only in TMDL: {tmdl_names - set(MEASURE_NAMES)}."
    )


def test_inventory_spec_matches_shipped_tmdl():
    """The shipped inventory table must expose the same measures as the spec."""
    with open(INVENTORY_TMDL, encoding="utf-8") as f:
        text = f.read()
    tmdl_names = set(re.findall(r"measure\s+'([^']+)'\s*=", text))
    assert set(INVENTORY_MEASURE_NAMES) == tmdl_names, (
        f"Drift between model_spec and inventory TMDL. "
        f"Only in spec: {set(INVENTORY_MEASURE_NAMES) - tmdl_names}. "
        f"Only in TMDL: {tmdl_names - set(INVENTORY_MEASURE_NAMES)}."
    )


def _column_refs(expression, table):
    """Bracketed column references in a DAX expression for a given table (table[Col])."""
    return set(re.findall(re.escape(table) + r"\[([^\]]+)\]", expression))


def test_measure_dax_refs_are_defined_columns():
    """Every column a measure references must be a defined friendly column (guards renames)."""
    fact_cols = set(FACT_COLUMN_NAMES)
    inv_cols = set(INVENTORY_COLUMN_NAMES)
    for m in MEASURES:
        refs = _column_refs(m["expression"], "governance_findings")
        assert refs <= fact_cols, f"{m['name']} references unknown findings columns: {refs - fact_cols}"
    for m in INVENTORY_MEASURES:
        refs = _column_refs(m["expression"], "governance_inventory")
        assert refs <= inv_cols, f"{m['name']} references unknown inventory columns: {refs - inv_cols}"


def _tmdl_column_map(path):
    """Map friendly column name -> sourceColumn from a TMDL table file."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    pairs = re.findall(r"column\s+'([^']+)'.*?sourceColumn:\s*(\S+)", text, re.DOTALL)
    return {name: src for name, src in pairs}


def test_fact_columns_match_shipped_tmdl():
    """Friendly column names + their Delta source columns must match the spec."""
    mapping = _tmdl_column_map(TMDL)
    spec = {c["name"]: c["source"] for c in FACT_COLUMNS}
    assert mapping == spec, f"Findings column drift. TMDL: {mapping}. Spec: {spec}."


def test_inventory_columns_match_shipped_tmdl():
    mapping = _tmdl_column_map(INVENTORY_TMDL)
    spec = {c["name"]: c["source"] for c in INVENTORY_COLUMNS}
    assert mapping == spec, f"Inventory column drift. TMDL: {mapping}. Spec: {spec}."
