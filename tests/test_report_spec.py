import os
import re

from fabric_bps.report import (
    INVENTORY_MEASURE_NAMES,
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
