"""Collect capacities via the Power BI admin API.

GET {PBI_BASE}/admin/capacities -> {"value": [ {id, displayName, sku, region, state, admins} ]}
"""
from __future__ import annotations

from .base import PBI_BASE, AdminClient


def collect_capacities(client: AdminClient) -> list:
    data = client.get(f"{PBI_BASE}/admin/capacities")
    capacities = []
    for c in data.get("value", []) or []:
        capacities.append(
            {
                "id": c.get("id"),
                "displayName": c.get("displayName"),
                "sku": c.get("sku"),
                "region": c.get("region"),
                "state": c.get("state"),
                "admins": c.get("admins", []) or [],
            }
        )
    return capacities
