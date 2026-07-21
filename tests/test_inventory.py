"""Tests for the resource inventory builder (admin control center)."""
import json
import pathlib

from fabric_bps.inventory import build_inventory
from fabric_bps.signals import Signals

SAMPLE = pathlib.Path(__file__).parent / "sample_signals_full.json"


def _by_name(items):
    return {i.name: i for i in items}


def test_full_sample_inventory_has_all_resources_and_no_orphans():
    signals = Signals.from_dict(json.loads(SAMPLE.read_text()))
    items = build_inventory(signals, run_id="run-1")

    # 3 workspaces + 1 capacity + 1 domain
    assert len(items) == 5
    types = sorted({i.resource_type for i in items})
    assert types == ["Capacity", "Domain", "Personal Workspace", "Workspace"]

    by_name = _by_name(items)
    assert by_name["Finance-Prod"].admin_count == 2
    assert by_name["Finance-Prod"].capacity_name == "Prod F64"
    assert by_name["Prod F64"].sku == "F64"

    # Well-formed sample: nothing is orphaned.
    assert all(i.is_orphan == "No" for i in items)
    assert all(i.orphan_reasons == "" for i in items)

    # Every row carries the run id and a timestamp for append-per-run trending.
    assert all(i.run_id == "run-1" and i.timestamp for i in items)


def test_orphan_detection():
    signals = Signals.from_dict(
        {
            "capacities": [
                {"id": "cap-used", "displayName": "Used", "sku": "F64", "state": "Active", "admins": ["a@x"]},
                {"id": "cap-idle", "displayName": "Idle", "sku": "F2", "state": "Paused", "admins": []},
            ],
            "workspaces": [
                # references a capacity that isn't in the capacities list -> missing capacity
                {"id": "w1", "name": "Ghost", "type": "Workspace", "state": "Active",
                 "capacityId": "cap-gone", "users": [{"groupUserAccessRight": "Admin"}]},
                # no role assignments at all
                {"id": "w2", "name": "Empty", "type": "Workspace", "state": "Active", "users": []},
                # deleted/removing state
                {"id": "w3", "name": "Deleting", "type": "Workspace", "state": "Deleted",
                 "capacityId": "cap-used", "users": [{"groupUserAccessRight": "Admin"}]},
                # members but no admin
                {"id": "w4", "name": "NoAdmin", "type": "Workspace", "state": "Active",
                 "capacityId": "cap-used", "users": [{"groupUserAccessRight": "Member"}]},
                # personal workspaces are never flagged
                {"id": "w5", "name": "Mine", "type": "PersonalGroup", "state": "Active", "users": []},
            ],
            "domains": [
                {"id": "dom-used", "displayName": "InUse"},
                {"id": "dom-empty", "displayName": "Unused"},
            ],
        }
    )
    items = build_inventory(signals, run_id="run-x")
    by_name = _by_name(items)

    assert by_name["Ghost"].is_orphan == "Yes"
    assert "references-missing-capacity" in by_name["Ghost"].orphan_reasons

    assert by_name["Empty"].is_orphan == "Yes"
    assert "no-role-assignments" in by_name["Empty"].orphan_reasons

    assert by_name["Deleting"].is_orphan == "Yes"
    assert "non-active-state" in by_name["Deleting"].orphan_reasons

    assert by_name["NoAdmin"].is_orphan == "Yes"
    assert "no-admins" in by_name["NoAdmin"].orphan_reasons

    # personal workspaces are descriptive-only, never orphaned
    assert by_name["Mine"].is_orphan == "No"
    assert by_name["Mine"].resource_type == "Personal Workspace"

    # capacity with no assigned workspaces AND no admins is doubly flagged
    assert by_name["Idle"].is_orphan == "Yes"
    assert "no-workspaces-assigned" in by_name["Idle"].orphan_reasons
    assert "no-admins" in by_name["Idle"].orphan_reasons

    # capacity that has an assigned workspace (w3 -> cap-used) is not orphaned
    assert by_name["Used"].is_orphan == "No"

    # domain with no assigned workspaces is flagged
    assert by_name["Unused"].is_orphan == "Yes"
    assert "no-workspaces-assigned" in by_name["Unused"].orphan_reasons


def test_to_row_columns_stable():
    signals = Signals.from_dict(json.loads(SAMPLE.read_text()))
    row = build_inventory(signals, run_id="r")[0].to_row()
    assert set(row) == {
        "run_id", "timestamp", "resource_type", "resource_id", "name", "state", "sku",
        "region", "on_dedicated_capacity", "capacity_name", "domain_name", "admin_count",
        "user_count", "is_orphan", "orphan_reasons",
    }
