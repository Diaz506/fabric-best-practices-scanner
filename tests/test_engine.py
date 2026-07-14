import json
import os

from fabric_bps import load_catalog, scan_from_signals
from fabric_bps.models import Status

HERE = os.path.dirname(__file__)


def load_sample():
    with open(os.path.join(HERE, "sample_signals.json"), encoding="utf-8") as f:
        return json.load(f)


def test_catalog_loads_both_dimensions():
    rules = load_catalog()
    dims = {r.dimension for r in rules}
    assert "tenant-settings" in dims
    assert "capacity-cost" in dims
    assert len(rules) >= 9


def test_dimension_filter():
    rules = load_catalog(dimensions=["capacity-cost"])
    assert rules
    assert all(r.dimension == "capacity-cost" for r in rules)


def test_scan_statuses():
    res = scan_from_signals(load_sample())
    by_id = {f.rule_id: f for f in res["findings"]}

    assert by_id["tenant.publish-to-web-restricted"].status == Status.GAP
    assert by_id["tenant.workspace-creation-restricted"].status == Status.ADHERED
    assert by_id["tenant.external-sharing-restricted"].status == Status.ADHERED
    assert by_id["tenant.export-data-controlled"].status == Status.INSUFFICIENT_DATA
    assert by_id["tenant.service-principal-admin-api-scoped"].status == Status.ADHERED

    assert by_id["capacity.no-trial-in-production"].status == Status.GAP
    assert by_id["capacity.admins-assigned"].status == Status.GAP
    assert by_id["capacity.utilization-monitored"].status == Status.VERIFY_APPLICABILITY
    assert by_id["capacity.paused-reviewed"].status == Status.ADHERED


def test_archetype_and_metadata():
    res = scan_from_signals(load_sample())
    assert res["context"]["archetype"] == "departmental-bi"
    for f in res["findings"]:
        assert f.run_id and f.timestamp
        assert 0 <= f.applicability_confidence <= 100


def test_not_applicable_when_excludes_rule():
    # startup-analytics tenants should not get the "no trial in production" rule.
    res = scan_from_signals(load_sample(), context_overrides={"archetype": "startup-analytics"})
    ids = {f.rule_id for f in res["findings"]}
    assert "capacity.no-trial-in-production" not in ids


def test_findings_serialize_to_rows():
    res = scan_from_signals(load_sample())
    row = res["findings"][0].to_row()
    for key in ("run_id", "rule_id", "dimension", "status", "impact", "evidence"):
        assert key in row
