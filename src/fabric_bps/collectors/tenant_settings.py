"""Collect tenant settings via the Fabric admin API.

GET {FABRIC_BASE}/admin/tenantsettings -> {"tenantSettings": [ {settingName, enabled, ...} ]}
Normalized into a dict keyed by settingName for O(1) rule lookups.
"""
from __future__ import annotations

from .base import FABRIC_BASE, AdminClient


def collect_tenant_settings(client: AdminClient) -> dict:
    data = client.get(f"{FABRIC_BASE}/admin/tenantsettings")
    settings = {}
    for s in data.get("tenantSettings", []) or []:
        name = s.get("settingName")
        if name:
            settings[name] = s
    return settings
