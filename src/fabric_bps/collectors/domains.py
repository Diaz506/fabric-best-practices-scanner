"""Collect domains via the Fabric admin API.

GET {FABRIC_BASE}/admin/domains -> {"domains": [ {id, displayName, parentDomainId, contributorsScope} ]}
"""
from __future__ import annotations

from .base import FABRIC_BASE, AdminClient


def collect_domains(client: AdminClient) -> list:
    data = client.get(f"{FABRIC_BASE}/admin/domains")
    domains = []
    for d in data.get("domains", []) or []:
        domains.append(
            {
                "id": d.get("id"),
                "displayName": d.get("displayName"),
                "parentDomainId": d.get("parentDomainId"),
                "contributorsScope": d.get("contributorsScope"),
            }
        )
    return domains
