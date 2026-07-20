"""Tests for the Lakehouse writer path routing and the deploy helpers' import-safety.

These run offline (no Fabric runtime); they use a fake Spark writer to assert the
correct target is chosen and verify the report package imports without sempy/notebookutils.
"""
import json
import os

from fabric_bps import load_catalog, scan_from_signals
from fabric_bps.writers import write_lakehouse

HERE = os.path.dirname(__file__)


class _FakeDeltaWriter:
    def __init__(self, sink):
        self._sink = sink

    def format(self, *_):
        return self

    def mode(self, *_):
        return self

    def option(self, *_a, **_k):
        return self

    def save(self, path):
        self._sink["save"] = path

    def saveAsTable(self, table):
        self._sink["saveAsTable"] = table


class _FakeDF:
    def __init__(self, sink):
        self.write = _FakeDeltaWriter(sink)


class _FakeSpark:
    def __init__(self):
        self.calls = {}

    def createDataFrame(self, rows):
        self.calls["rows"] = len(rows)
        return _FakeDF(self.calls)


def _findings():
    with open(os.path.join(HERE, "sample_signals.json"), encoding="utf-8") as f:
        signals = json.load(f)
    return scan_from_signals(signals, dimensions=None)["findings"]


def test_writer_uses_saveastable_by_default():
    spark = _FakeSpark()
    out = write_lakehouse(_findings(), table="governance_findings", spark=spark)
    assert spark.calls.get("saveAsTable") == "governance_findings"
    assert "save" not in spark.calls
    assert "governance_findings" in out


def test_writer_saves_by_path_when_abfss_given():
    spark = _FakeSpark()
    abfss = "abfss://ws@onelake.dfs.fabric.microsoft.com/lh-id"
    out = write_lakehouse(
        _findings(), table="governance_findings", spark=spark, lakehouse_abfss=abfss
    )
    assert spark.calls.get("save") == f"{abfss}/Tables/governance_findings"
    assert "saveAsTable" not in spark.calls
    assert abfss in out


def test_report_package_imports_offline():
    """Provision/deploy helpers must import without the Fabric runtime present."""
    from fabric_bps.report import deploy_semantic_model, provision_lakehouse

    assert callable(provision_lakehouse)
    assert callable(deploy_semantic_model)
