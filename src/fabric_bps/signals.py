"""Normalized tenant governance signals collected from Fabric / Power BI admin APIs.

Collectors populate a Signals object; the engine only reads from it. This keeps the
rule-evaluation logic fully decoupled from the API calls, so the engine is testable
offline with sample signals (no live tenant required).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Signals:
    # name -> raw tenant setting object
    # (settingName, enabled, canSpecifySecurityGroups, enabledSecurityGroups, ...)
    tenant_settings: dict = field(default_factory=dict)
    capacities: list = field(default_factory=list)
    workspaces: list = field(default_factory=list)
    labels: list = field(default_factory=list)
    domains: list = field(default_factory=list)
    activity_available: bool = False
    meta: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Signals":
        d = d or {}
        return cls(
            tenant_settings=d.get("tenant_settings", {}) or {},
            capacities=d.get("capacities", []) or [],
            workspaces=d.get("workspaces", []) or [],
            labels=d.get("labels", []) or [],
            domains=d.get("domains", []) or [],
            activity_available=bool(d.get("activity_available", False)),
            meta=d.get("meta", {}) or {},
        )

    def tenant_setting(self, name: str) -> Optional[dict]:
        return self.tenant_settings.get(name)
