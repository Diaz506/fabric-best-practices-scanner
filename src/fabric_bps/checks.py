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


@check("capacity_uses_fabric_sku")
def capacity_uses_fabric_sku(sig: Signals, params: dict):
    """Prefer Fabric (F) SKUs over legacy Power BI Premium/embedded (P/EM/A) SKUs."""
    caps = sig.capacities
    if not caps:
        return Status.INSUFFICIENT_DATA, {"reason": "no capacities collected"}
    legacy = []
    for c in caps:
        sku = _sku(c)
        if not sku or sku.startswith("trial"):
            continue  # trial handled by its own rule
        if not sku.startswith("f"):
            legacy.append(c.get("displayName"))
    if legacy:
        return Status.VERIFY_APPLICABILITY, {
            "legacySkuCapacities": [x for x in legacy if x][:25],
            "reason": "capacities on legacy P/EM/A SKUs; plan migration to Fabric (F) SKUs",
        }
    return Status.ADHERED, {"capacityCount": len(caps)}


@check("capacity_region_consistency")
def capacity_region_consistency(sig: Signals, params: dict):
    """Multiple capacity regions can signal data-residency drift; confirm it's intentional."""
    caps = sig.capacities
    if not caps:
        return Status.INSUFFICIENT_DATA, {"reason": "no capacities collected"}
    regions = sorted({str(c.get("region") or "").strip() for c in caps if c.get("region")})
    if not regions:
        return Status.INSUFFICIENT_DATA, {"reason": "capacity region not collected"}
    if len(regions) <= 1:
        return Status.ADHERED, {"regions": regions}
    return Status.VERIFY_APPLICABILITY, {
        "regions": regions,
        "reason": "capacities span multiple regions; confirm this is intentional (data residency/latency)",
    }


@check("capacity_min_admins")
def capacity_min_admins(sig: Signals, params: dict):
    """Each capacity should have at least N admins so no single person is a bottleneck."""
    minimum = int(params.get("minimum", 2))
    caps = sig.capacities
    if not caps:
        return Status.INSUFFICIENT_DATA, {"reason": "no capacities collected"}
    if all(not (c.get("admins")) for c in caps):
        return Status.INSUFFICIENT_DATA, {"reason": "capacity admins not collected"}
    low = [c.get("displayName") for c in caps if len(c.get("admins") or []) < minimum]
    if low:
        return Status.GAP, {"capacitiesBelowMinAdmins": [x for x in low if x][:25], "minimum": minimum}
    return Status.ADHERED, {"capacityCount": len(caps), "minimum": minimum}


# --- Workspace governance ---------------------------------------------------

def _real_workspaces(sig: Signals) -> list:
    """Non-personal workspaces (exclude PersonalGroup 'My workspace' entries)."""
    return [
        w
        for w in (sig.workspaces or [])
        if str(w.get("type") or "").lower() not in ("personalgroup", "personal")
    ]


def _admin_count(w: dict) -> int:
    return sum(
        1
        for u in (w.get("users") or [])
        if str(u.get("groupUserAccessRight") or u.get("workspaceUserAccessRight") or "").lower()
        == "admin"
    )


@check("workspaces_on_dedicated_capacity")
def workspaces_on_dedicated_capacity(sig: Signals, params: dict):
    ws = _real_workspaces(sig)
    if not ws:
        return Status.INSUFFICIENT_DATA, {"reason": "no workspaces collected"}
    shared = [w.get("name") for w in ws if not w.get("isOnDedicatedCapacity")]
    if shared:
        return Status.GAP, {"sharedCapacityWorkspaces": [s for s in shared if s][:25]}
    return Status.ADHERED, {"workspaceCount": len(ws)}


@check("workspaces_have_minimum_admins")
def workspaces_have_minimum_admins(sig: Signals, params: dict):
    minimum = int(params.get("minimum", 2))
    ws = _real_workspaces(sig)
    if not ws:
        return Status.INSUFFICIENT_DATA, {"reason": "no workspaces collected"}
    if all(not (w.get("users")) for w in ws):
        return Status.INSUFFICIENT_DATA, {"reason": "workspace role membership not collected"}
    low = [w.get("name") for w in ws if _admin_count(w) < minimum]
    if low:
        return Status.GAP, {"workspacesBelowMinAdmins": [s for s in low if s][:25], "minimum": minimum}
    return Status.ADHERED, {"workspaceCount": len(ws), "minimum": minimum}


@check("personal_workspaces_reviewed")
def personal_workspaces_reviewed(sig: Signals, params: dict):
    threshold = int(params.get("threshold", 25))
    if not sig.workspaces:
        return Status.INSUFFICIENT_DATA, {"reason": "no workspaces collected"}
    personal = [
        w for w in sig.workspaces if str(w.get("type") or "").lower() in ("personalgroup", "personal")
    ]
    if len(personal) > threshold:
        return Status.VERIFY_APPLICABILITY, {
            "personalWorkspaceCount": len(personal),
            "reason": "high number of personal workspaces; confirm they hold no shared/governed content",
        }
    return Status.ADHERED, {"personalWorkspaceCount": len(personal)}


@check("workspaces_in_active_state")
def workspaces_in_active_state(sig: Signals, params: dict):
    """Flag workspaces in non-active states (Orphaned/Deleted/Removing) for cleanup."""
    ws = _real_workspaces(sig)
    if not ws:
        return Status.INSUFFICIENT_DATA, {"reason": "no workspaces collected"}
    if all(not w.get("state") for w in ws):
        return Status.INSUFFICIENT_DATA, {"reason": "workspace state not collected"}
    non_active = [
        w.get("name")
        for w in ws
        if w.get("state") and str(w.get("state")).lower() != "active"
    ]
    if non_active:
        return Status.GAP, {
            "nonActiveWorkspaces": [x for x in non_active if x][:25],
            "reason": "workspaces in Orphaned/Deleted/Removing states should be cleaned up or reassigned",
        }
    return Status.ADHERED, {"workspaceCount": len(ws)}


@check("workspaces_have_role_assignments")
def workspaces_have_role_assignments(sig: Signals, params: dict):
    """A workspace with no explicit role assignments is ungoverned."""
    ws = _real_workspaces(sig)
    if not ws:
        return Status.INSUFFICIENT_DATA, {"reason": "no workspaces collected"}
    if all(not (w.get("users")) for w in ws):
        return Status.INSUFFICIENT_DATA, {"reason": "workspace role membership not collected"}
    ungoverned = [w.get("name") for w in ws if not (w.get("users") or [])]
    if ungoverned:
        return Status.GAP, {
            "workspacesWithoutRoleAssignments": [x for x in ungoverned if x][:25],
            "reason": "workspaces with no explicit role assignments are ungoverned",
        }
    return Status.ADHERED, {"workspaceCount": len(ws)}


# --- Roles & access ---------------------------------------------------------

@check("workspace_roles_group_based")
def workspace_roles_group_based(sig: Signals, params: dict):
    threshold = float(params.get("threshold", 0.5))
    ws = _real_workspaces(sig)
    users = [u for w in ws for u in (w.get("users") or [])]
    if not users:
        return Status.INSUFFICIENT_DATA, {"reason": "workspace role membership not collected"}
    direct = [u for u in users if str(u.get("principalType") or "").lower() == "user"]
    ratio = len(direct) / len(users)
    if ratio > threshold:
        return Status.GAP, {
            "directUserAssignments": len(direct),
            "totalAssignments": len(users),
            "reason": "most access is granted to individual users rather than security groups",
        }
    return Status.ADHERED, {"directUserRatio": round(ratio, 2)}


@check("workspace_admin_sprawl")
def workspace_admin_sprawl(sig: Signals, params: dict):
    maximum = int(params.get("maximum", 5))
    ws = _real_workspaces(sig)
    if not ws or all(not (w.get("users")) for w in ws):
        return Status.INSUFFICIENT_DATA, {"reason": "workspace role membership not collected"}
    sprawling = [w.get("name") for w in ws if _admin_count(w) > maximum]
    if sprawling:
        return Status.GAP, {"workspacesOverAdminLimit": [s for s in sprawling if s][:25], "maximum": maximum}
    return Status.ADHERED, {"maximum": maximum}


# --- Domains & data mesh -----------------------------------------------------

@check("domains_defined")
def domains_defined(sig: Signals, params: dict):
    if sig.domains is None:
        return Status.INSUFFICIENT_DATA, {"reason": "domains not collected"}
    if len(sig.domains) == 0:
        return Status.GAP, {"domainCount": 0}
    return Status.ADHERED, {"domainCount": len(sig.domains)}


@check("workspaces_assigned_to_domains")
def workspaces_assigned_to_domains(sig: Signals, params: dict):
    threshold = float(params.get("threshold", 0.6))
    ws = _real_workspaces(sig)
    if not ws:
        return Status.INSUFFICIENT_DATA, {"reason": "no workspaces collected"}
    if all(w.get("domainId") is None for w in ws):
        return Status.INSUFFICIENT_DATA, {"reason": "workspace domain assignment not collected"}
    assigned = [w for w in ws if w.get("domainId")]
    ratio = len(assigned) / len(ws)
    if ratio < threshold:
        return Status.GAP, {"assigned": len(assigned), "total": len(ws), "ratio": round(ratio, 2)}
    return Status.ADHERED, {"ratio": round(ratio, 2)}


@check("domains_contributors_scoped")
def domains_contributors_scoped(sig: Signals, params: dict):
    """Domain contributor assignment should be scoped, not open to the whole tenant."""
    if sig.domains is None:
        return Status.INSUFFICIENT_DATA, {"reason": "domains not collected"}
    if len(sig.domains) == 0:
        return Status.INSUFFICIENT_DATA, {"reason": "no domains defined"}
    if all(d.get("contributorsScope") is None for d in sig.domains):
        return Status.INSUFFICIENT_DATA, {"reason": "domain contributorsScope not collected"}
    open_domains = [
        d.get("displayName")
        for d in sig.domains
        if str(d.get("contributorsScope") or "").lower() == "alltenant"
    ]
    if open_domains:
        return Status.GAP, {
            "openContributorDomains": [x for x in open_domains if x][:25],
            "reason": "domains where any tenant user can contribute; scope to specific users/groups",
        }
    return Status.ADHERED, {"domainCount": len(sig.domains)}


# --- Monitoring & deployment -------------------------------------------------

@check("deployment_pipelines_used")
def deployment_pipelines_used(sig: Signals, params: dict):
    pipelines = sig.meta.get("pipelines")
    if pipelines is None:
        return Status.INSUFFICIENT_DATA, {"reason": "deployment pipelines not collected"}
    if len(pipelines) == 0:
        return Status.GAP, {"pipelineCount": 0}
    return Status.ADHERED, {"pipelineCount": len(pipelines)}


@check("audit_log_accessible")
def audit_log_accessible(sig: Signals, params: dict):
    if sig.activity_available:
        return Status.ADHERED, {"reason": "activity/audit events are accessible"}
    return Status.VERIFY_APPLICABILITY, {
        "reason": "audit-log access could not be confirmed in this run; verify audit retention and access",
    }
