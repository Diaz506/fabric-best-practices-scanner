"""Collect content-level metadata via the Power BI Scanner (metadata scanning) API.

The list/admin APIs describe *containers* (workspaces, capacities, domains) but not the
*content* inside them. The Scanner API returns per-artifact governance metadata — endorsement,
sensitivity labels, row-level security, storage mode, ownership — which unlocks content-posture
rules that would otherwise be impossible.

Three-step async flow, batched at <=100 workspaces per scan:
  1. POST /admin/workspaces/getInfo?lineage=true&datasourceDetails=true&datasetSchema=true&getArtifactUsers=true
        body {"workspaces": [ids]}         -> {"id": scanId, "status": "..."}
  2. GET  /admin/workspaces/scanStatus/{scanId}   -> poll until status == "Succeeded"
  3. GET  /admin/workspaces/scanResult/{scanId}   -> {"workspaces": [ {datasets, reports, ...} ]}

Prerequisite (tenant admin, one-time): enable "Enhance admin APIs responses with detailed
metadata" (and, for artifact user lists, "...with detailed metadata of users"). Without it the
scan still runs but omits the fields these rules read, so the content rules report
insufficient-data rather than a false verdict.
"""
from __future__ import annotations

import time

from .base import PBI_BASE, AdminClient

# (scanResult key, normalized itemType)
_ARTIFACT_TYPES = [
    ("datasets", "Dataset"),
    ("reports", "Report"),
    ("dashboards", "Dashboard"),
    ("dataflows", "Dataflow"),
    ("datamarts", "Datamart"),
]


def _batched(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _endorsement(obj: dict) -> str:
    return (obj.get("endorsementDetails") or {}).get("endorsement") or "None"


def _has_label(obj: dict) -> bool:
    return bool((obj.get("sensitivityLabel") or {}).get("labelId"))


def _dataset_has_rls(ds: dict) -> bool:
    """A dataset enforces RLS when any role defines a table filter expression."""
    for role in ds.get("roles") or []:
        for tp in role.get("tablePermissions") or []:
            if (tp.get("filterExpression") or "").strip():
                return True
    return False


def flatten_scan_result(result: dict) -> list:
    """Flatten a Scanner API scanResult into one normalized row per artifact.

    Pure function (no I/O) so it is unit-testable with a recorded scanResult payload.
    """
    items: list = []
    for ws in (result or {}).get("workspaces", []) or []:
        ws_id, ws_name = ws.get("id"), ws.get("name")
        dataset_ids = {d.get("id") for d in ws.get("datasets") or [] if d.get("id")}
        for key, item_type in _ARTIFACT_TYPES:
            for a in ws.get(key) or []:
                item = {
                    "workspaceId": ws_id,
                    "workspaceName": ws_name,
                    "itemType": item_type,
                    "id": a.get("id"),
                    "name": a.get("name"),
                    "endorsement": _endorsement(a),
                    "hasSensitivityLabel": _has_label(a),
                    "sensitivityLabelId": (a.get("sensitivityLabel") or {}).get("labelId", ""),
                    "configuredBy": a.get("configuredBy", ""),
                }
                if item_type == "Dataset":
                    item["hasRls"] = _dataset_has_rls(a)
                    item["storageMode"] = a.get("targetStorageMode", "")
                if item_type == "Report":
                    ds_id = a.get("datasetId")
                    item["datasetId"] = ds_id or ""
                    item["orphaned"] = bool(ds_id) and ds_id not in dataset_ids
                items.append(item)
    return items


def collect_scanner_items(
    client: AdminClient,
    workspace_ids,
    batch_size: int = 100,
    poll_interval: float = 2.0,
    max_polls: int = 60,
) -> list:
    """Run the Scanner API over the given workspace ids and return flattened artifact rows.

    Returns an empty list when there are no workspaces to scan. Batches of <=100 keep each
    scan within the API limit; each batch is polled to completion before its result is read.
    """
    ids = [w for w in (workspace_ids or []) if w]
    if not ids:
        return []

    params = {
        "lineage": "true",
        "datasourceDetails": "true",
        "datasetSchema": "true",
        "datasetExpressions": "false",
        "getArtifactUsers": "true",
    }
    items: list = []
    for batch in _batched(ids, batch_size):
        scan = client.post(
            f"{PBI_BASE}/admin/workspaces/getInfo",
            params=params,
            json={"workspaces": list(batch)},
        )
        scan_id = scan.get("id")
        if not scan_id:
            continue
        for _ in range(max_polls):
            status = client.get(f"{PBI_BASE}/admin/workspaces/scanStatus/{scan_id}")
            state = str(status.get("status") or "").lower()
            if state in ("succeeded", "failed", "error"):
                break
            time.sleep(poll_interval)
        result = client.get(f"{PBI_BASE}/admin/workspaces/scanResult/{scan_id}")
        items.extend(flatten_scan_result(result))
    return items
