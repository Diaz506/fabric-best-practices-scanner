import json
import os

from fabric_bps import load_catalog, scan_from_signals
from fabric_bps.models import Status

HERE = os.path.dirname(__file__)


def load_sample():
    with open(os.path.join(HERE, "sample_signals.json"), encoding="utf-8") as f:
        return json.load(f)


def load_full_sample():
    with open(os.path.join(HERE, "sample_signals_full.json"), encoding="utf-8") as f:
        return json.load(f)


def test_catalog_loads_both_dimensions():
    rules = load_catalog()
    dims = {r.dimension for r in rules}
    assert "tenant-settings" in dims
    assert "capacity-cost" in dims
    assert len(rules) >= 9


def test_catalog_loads_all_seven_dimensions():
    rules = load_catalog()
    dims = {r.dimension for r in rules}
    expected = {
        "tenant-settings",
        "capacity-cost",
        "workspace-governance",
        "roles-access",
        "domains-data-mesh",
        "data-security",
        "monitoring-deployment",
    }
    assert expected.issubset(dims)


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


def test_full_sample_archetype_is_data_mesh():
    res = scan_from_signals(load_full_sample())
    assert res["context"]["archetype"] == "data-mesh-adopter"


def test_new_dimension_statuses():
    res = scan_from_signals(load_full_sample())
    by_id = {f.rule_id: f for f in res["findings"]}

    # Workspace governance
    assert by_id["workspace.on-dedicated-capacity"].status == Status.GAP
    assert by_id["workspace.minimum-admins"].status == Status.GAP
    assert by_id["workspace.personal-workspaces-reviewed"].status == Status.ADHERED

    # Roles & access
    assert by_id["roles.group-based-access"].status == Status.GAP
    assert by_id["roles.admin-sprawl"].status == Status.ADHERED

    # Domains & data mesh
    assert by_id["domains.defined"].status == Status.ADHERED
    assert by_id["domains.workspaces-assigned"].status == Status.GAP
    assert by_id["domains.contributors-scoped"].status == Status.ADHERED

    # New capacity checks (Prod F64, single region, single admin)
    assert by_id["capacity.fabric-sku-preferred"].status == Status.ADHERED
    assert by_id["capacity.region-consistency"].status == Status.ADHERED
    assert by_id["capacity.resilient-admins"].status == Status.GAP

    # New workspace checks (all Active, all have role assignments)
    assert by_id["workspace.no-orphaned-state"].status == Status.ADHERED
    assert by_id["workspace.governed-access"].status == Status.ADHERED

    # Data security
    assert by_id["security.information-protection-enabled"].status == Status.ADHERED

    # Monitoring & deployment
    assert by_id["monitoring.deployment-pipelines"].status == Status.ADHERED
    assert by_id["monitoring.audit-log-accessible"].status == Status.ADHERED


def test_private_link_dropped_for_non_regulated():
    # Low base confidence + medium impact -> silently dropped for a non-regulated tenant.
    res = scan_from_signals(load_full_sample())
    ids = {f.rule_id for f in res["findings"]}
    assert "security.private-link" not in ids


def test_no_workspaces_on_paused_capacity_adhered():
    # Full sample: the only capacity is Active -> no stranded workspaces.
    res = scan_from_signals(load_full_sample())
    by_id = {f.rule_id: f for f in res["findings"]}
    assert by_id["capacity.no-workspaces-on-paused-capacity"].status == Status.ADHERED


def test_no_workspaces_on_paused_capacity_gap_when_stranded():
    # A suspended capacity that still has a workspace assigned is an outage risk (GAP).
    sig = load_full_sample()
    for c in sig["capacities"]:
        if c.get("id") == "cap-1":
            c["state"] = "Suspended"
    res = scan_from_signals(sig)
    finding = {f.rule_id: f for f in res["findings"]}["capacity.no-workspaces-on-paused-capacity"]
    assert finding.status == Status.GAP
    assert finding.evidence["strandedCount"] >= 1
