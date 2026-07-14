"""Collect deployment pipelines via the Power BI admin API.

GET {PBI_BASE}/admin/pipelines -> {"value": [ {id, displayName, stages} ]}
"""
from __future__ import annotations

from .base import PBI_BASE, AdminClient


def collect_pipelines(client: AdminClient) -> list:
    data = client.get(f"{PBI_BASE}/admin/pipelines")
    pipelines = []
    for p in data.get("value", []) or []:
        pipelines.append(
            {
                "id": p.get("id"),
                "displayName": p.get("displayName"),
                "stages": p.get("stages", []) or [],
            }
        )
    return pipelines
