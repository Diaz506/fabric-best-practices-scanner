"""Resource inventory for the admin control center.

Turns the collected signals (workspaces, capacities, domains) into a flat, one-row-per-
resource inventory with orphan/unused flags. Written to its own ``governance_inventory``
Delta table (append-per-run, like findings) so the Power BI report can offer an Inventory
page and an Orphans page for admin visibility.

Kept separate from the findings engine: inventory is descriptive (what exists), findings
are evaluative (what to fix).
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from .signals import Signals

_PERSONAL_TYPES = ("personalgroup", "personal")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _admin_count(w: dict) -> int:
    return sum(
        1
        for u in (w.get("users") or [])
        if str(u.get("groupUserAccessRight") or u.get("workspaceUserAccessRight") or "").lower()
        == "admin"
    )


@dataclass
class InventoryItem:
    run_id: Optional[str]
    timestamp: Optional[str]
    resource_type: str
    resource_id: Optional[str]
    name: Optional[str]
    state: str = ""
    sku: str = ""
    region: str = ""
    on_dedicated_capacity: str = ""
    capacity_name: str = ""
    domain_name: str = ""
    admin_count: int = 0
    user_count: int = 0
    is_orphan: str = "No"
    orphan_reasons: str = ""

    def to_row(self) -> dict:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "name": self.name,
            "state": self.state,
            "sku": self.sku,
            "region": self.region,
            "on_dedicated_capacity": self.on_dedicated_capacity,
            "capacity_name": self.capacity_name,
            "domain_name": self.domain_name,
            "admin_count": self.admin_count,
            "user_count": self.user_count,
            "is_orphan": self.is_orphan,
            "orphan_reasons": self.orphan_reasons,
        }


def _mk(reasons: list, **kwargs) -> InventoryItem:
    reasons = [r for r in reasons if r]
    return InventoryItem(
        is_orphan="Yes" if reasons else "No",
        orphan_reasons=", ".join(reasons),
        **kwargs,
    )


def build_inventory(signals: Signals, run_id: str = None, timestamp: str = None) -> list:
    """Build the resource inventory (workspaces, capacities, domains) with orphan flags."""
    ts = timestamp or _now_iso()
    items: list = []

    capacities = signals.capacities or []
    workspaces = signals.workspaces or []
    domains = signals.domains or []

    cap_by_id = {c.get("id"): c for c in capacities if c.get("id")}
    ws_capacity_ids = {w.get("capacityId") for w in workspaces if w.get("capacityId")}
    ws_domain_ids = {w.get("domainId") for w in workspaces if w.get("domainId")}

    # --- Workspaces --------------------------------------------------------
    for w in workspaces:
        wtype = str(w.get("type") or "").lower()
        personal = wtype in _PERSONAL_TYPES
        users = w.get("users") or []
        admins = _admin_count(w)
        cap_id = w.get("capacityId")
        state = str(w.get("state") or "")

        reasons: list = []
        if not personal:
            if state and state.lower() != "active":
                reasons.append("non-active-state")
            if not users:
                reasons.append("no-role-assignments")
            elif admins == 0:
                reasons.append("no-admins")
            if cap_id and cap_id not in cap_by_id:
                reasons.append("references-missing-capacity")

        items.append(
            _mk(
                reasons,
                run_id=run_id,
                timestamp=ts,
                resource_type="Personal Workspace" if personal else "Workspace",
                resource_id=w.get("id"),
                name=w.get("name"),
                state=state,
                on_dedicated_capacity="Yes" if w.get("isOnDedicatedCapacity") else "No",
                capacity_name=(cap_by_id.get(cap_id) or {}).get("displayName", "") if cap_id else "",
                domain_name="",  # domain display resolved on the domain rows
                admin_count=admins,
                user_count=len(users),
            )
        )

    # --- Capacities --------------------------------------------------------
    for c in capacities:
        admins = c.get("admins") or []
        reasons = []
        if c.get("id") not in ws_capacity_ids:
            reasons.append("no-workspaces-assigned")
        if not admins:
            reasons.append("no-admins")
        items.append(
            _mk(
                reasons,
                run_id=run_id,
                timestamp=ts,
                resource_type="Capacity",
                resource_id=c.get("id"),
                name=c.get("displayName"),
                state=str(c.get("state") or ""),
                sku=str(c.get("sku") or ""),
                region=str(c.get("region") or ""),
                admin_count=len(admins),
            )
        )

    # --- Domains -----------------------------------------------------------
    for d in domains:
        reasons = []
        if d.get("id") not in ws_domain_ids:
            reasons.append("no-workspaces-assigned")
        items.append(
            _mk(
                reasons,
                run_id=run_id,
                timestamp=ts,
                resource_type="Domain",
                resource_id=d.get("id"),
                name=d.get("displayName"),
            )
        )

    return items
