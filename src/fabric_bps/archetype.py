"""Archetype classifier.

Derives the customer context (archetype + flags) from collected signals, with optional
overrides. The archetype is the single, explainable decision that seeds "what matters"
for this customer; per-rule applicability confidence refines it from there.

Archetypes: regulated-enterprise | large-enterprise | data-mesh-adopter |
             departmental-bi | startup-analytics
"""
from __future__ import annotations

from .signals import Signals


def classify(signals: Signals, overrides: dict = None) -> dict:
    overrides = overrides or {}
    workspaces = signals.workspaces or []
    capacities = signals.capacities or []
    domains = signals.domains or []
    labels = signals.labels or []

    n_ws = len(workspaces)
    has_domains = len(domains) > 0
    has_labels = len(labels) > 0
    only_trial = bool(capacities) and all(
        str(c.get("sku") or "").lower().startswith("trial") for c in capacities
    )

    if overrides.get("archetype"):
        archetype = overrides["archetype"]
    elif has_domains:
        archetype = "data-mesh-adopter"
    elif (only_trial or not capacities) and n_ws <= 5:
        archetype = "startup-analytics"
    elif has_labels or overrides.get("regulated"):
        archetype = "regulated-enterprise"
    elif n_ws >= 50:
        archetype = "large-enterprise"
    else:
        archetype = "departmental-bi"

    context = {
        "archetype": archetype,
        "workspace_count": n_ws,
        "capacity_count": len(capacities),
        "has_domains": has_domains,
        "has_sensitive_data": bool(has_labels) or bool(overrides.get("has_sensitive_data")),
        "regulated": bool(overrides.get("regulated")) or archetype == "regulated-enterprise",
    }
    # Overrides win and may add extra context keys used by rule conditions.
    for k, v in overrides.items():
        context[k] = v
    return context
