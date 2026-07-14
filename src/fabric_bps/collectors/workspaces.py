"""Collect workspaces (with role memberships) via the Power BI admin API.

GET {PBI_BASE}/admin/groups?$top=5000&$expand=users
  -> {"value": [ {id, name, type, state, isOnDedicatedCapacity, capacityId, users:[...]} ]}
"""
from __future__ import annotations

from .base import PBI_BASE, AdminClient


def collect_workspaces(client: AdminClient, top: int = 5000) -> list:
    data = client.get(f"{PBI_BASE}/admin/groups", params={"$top": top, "$expand": "users"})
    workspaces = []
    for w in data.get("value", []) or []:
        workspaces.append(
            {
                "id": w.get("id"),
                "name": w.get("name"),
                "type": w.get("type"),
                "state": w.get("state"),
                "isOnDedicatedCapacity": w.get("isOnDedicatedCapacity"),
                "capacityId": w.get("capacityId"),
                "domainId": w.get("domainId"),  # populated by the Scanner API when available
                "users": w.get("users", []) or [],
            }
        )
    return workspaces
