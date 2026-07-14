"""Reusable check primitives.

Rules in the YAML catalog reference a check by name (declarative), and the check
runs the actual Python logic against collected signals. Each check returns
(Status, evidence_dict). Keeping checks small and reusable lets the catalog stay
data-only while the logic stays testable.
"""
from __future__ import annotations

from typing import Callable

from .models import Status
from .signals import Signals

CheckFn = Callable[[Signals, dict], tuple]
_REGISTRY: dict = {}


def check(name: str):
    def deco(fn: CheckFn) -> CheckFn:
        _REGISTRY[name] = fn
        return fn

    return deco


def get_check(name: str) -> CheckFn:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown check primitive: {name!r}")
    return _REGISTRY[name]


def registered_checks() -> list:
    return sorted(_REGISTRY.keys())


# --- Tenant settings ---------------------------------------------------------

def _setting_scope(s: dict):
    """Return ('disabled'|'limited'|'org', groups) for a tenant setting object."""
    enabled = s.get("enabled")
    groups = s.get("enabledSecurityGroups") or []
    if enabled is False:
        return "disabled", groups
    if s.get("canSpecifySecurityGroups") and groups:
        return "limited", groups
    if enabled is True:
        return "org", groups
    return "unknown", groups


@check("tenant_setting_is_disabled")
def tenant_setting_is_disabled(sig: Signals, params: dict):
    """Good when the setting is OFF (e.g. Publish-to-Web)."""
    name = params["setting"]
    s = sig.tenant_setting(name)
    if s is None:
        return Status.INSUFFICIENT_DATA, {"setting": name, "reason": "not collected"}
    scope, groups = _setting_scope(s)
    if scope == "disabled":
        return Status.ADHERED, {"setting": name, "scope": "disabled"}
    if scope == "limited":
        return Status.VERIFY_APPLICABILITY, {
            "setting": name,
            "scope": "limited-to-groups",
            "groups": [g.get("name") for g in groups],
            "reason": "enabled for a subset; confirm the scope is intentional",
        }
    if scope == "org":
        return Status.GAP, {"setting": name, "scope": "entire-org"}
    return Status.INSUFFICIENT_DATA, {"setting": name, "reason": "unknown state"}


@check("tenant_setting_is_restricted")
def tenant_setting_is_restricted(sig: Signals, params: dict):
    """Good when the setting is NOT enabled for the entire org (off or group-scoped)."""
    name = params["setting"]
    s = sig.tenant_setting(name)
    if s is None:
        return Status.INSUFFICIENT_DATA, {"setting": name, "reason": "not collected"}
    scope, groups = _setting_scope(s)
    if scope == "disabled":
        return Status.ADHERED, {"setting": name, "scope": "disabled"}
    if scope == "limited":
        return Status.ADHERED, {
            "setting": name,
            "scope": "limited-to-groups",
            "groups": [g.get("name") for g in groups],
        }
    if scope == "org":
        return Status.GAP, {"setting": name, "scope": "entire-org"}
    return Status.INSUFFICIENT_DATA, {"setting": name, "reason": "unknown state"}


@check("tenant_setting_is_enabled")
def tenant_setting_is_enabled(sig: Signals, params: dict):
    """Good when the setting is ON (e.g. a protective control)."""
    name = params["setting"]
    s = sig.tenant_setting(name)
    if s is None:
        return Status.INSUFFICIENT_DATA, {"setting": name, "reason": "not collected"}
    if s.get("enabled") is True:
        return Status.ADHERED, {"setting": name, "scope": "enabled"}
    if s.get("enabled") is False:
        return Status.GAP, {"setting": name, "scope": "disabled"}
    return Status.INSUFFICIENT_DATA, {"setting": name, "reason": "unknown state"}


# --- Capacity & cost ---------------------------------------------------------

def _sku(c: dict) -> str:
    return str(c.get("sku") or "").lower()


@check("capacity_no_trial_in_production")
def capacity_no_trial_in_production(sig: Signals, params: dict):
    caps = sig.capacities
    if not caps:
        return Status.INSUFFICIENT_DATA, {"reason": "no capacities collected"}
    trials = [c.get("displayName") for c in caps if _sku(c).startswith("trial") or _sku(c) == ""]
    if trials:
        return Status.GAP, {"trialCapacities": [t for t in trials if t]}
    return Status.ADHERED, {"capacityCount": len(caps)}


@check("capacity_admins_assigned")
def capacity_admins_assigned(sig: Signals, params: dict):
    caps = sig.capacities
    if not caps:
        return Status.INSUFFICIENT_DATA, {"reason": "no capacities collected"}
    missing = [c.get("displayName") for c in caps if not (c.get("admins") or [])]
    if missing:
        return Status.GAP, {"capacitiesWithoutAdmins": [m for m in missing if m]}
    return Status.ADHERED, {"capacityCount": len(caps)}


@check("capacity_metrics_monitored")
def capacity_metrics_monitored(sig: Signals, params: dict):
    if not sig.capacities:
        return Status.INSUFFICIENT_DATA, {"reason": "no capacities collected"}
    if sig.meta.get("capacity_metrics_available"):
        return Status.ADHERED, {"reason": "capacity metrics reported as available"}
    return Status.VERIFY_APPLICABILITY, {
        "reason": "Capacity Metrics app install is not verifiable via API; confirm monitoring is in place",
    }


@check("capacity_not_paused")
def capacity_not_paused(sig: Signals, params: dict):
    caps = sig.capacities
    if not caps:
        return Status.INSUFFICIENT_DATA, {"reason": "no capacities collected"}
    paused = [c.get("displayName") for c in caps if str(c.get("state") or "").lower() in ("paused", "suspended")]
    if paused:
        return Status.VERIFY_APPLICABILITY, {
            "pausedCapacities": [p for p in paused if p],
            "reason": "paused/suspended may be intentional cost control; confirm",
        }
    return Status.ADHERED, {"activeCapacities": len(caps)}
