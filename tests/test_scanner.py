"""Tests for the Scanner API collector: result flattening and the async scan flow."""
from fabric_bps.collectors import collect_scanner_items, flatten_scan_result

_SCAN_RESULT = {
    "workspaces": [
        {
            "id": "ws-1",
            "name": "Finance-Prod",
            "datasets": [
                {
                    "id": "ds-a",
                    "name": "Finance Model",
                    "configuredBy": "u1@contoso.com",
                    "endorsementDetails": {"endorsement": "Certified"},
                    "sensitivityLabel": {"labelId": "lbl-conf"},
                    "targetStorageMode": "Import",
                    "roles": [
                        {
                            "name": "RegionRole",
                            "tablePermissions": [
                                {"name": "Sales", "filterExpression": "[Region] = \"West\""}
                            ],
                        }
                    ],
                },
                {
                    "id": "ds-b",
                    "name": "Scratch Model",
                    "endorsementDetails": {},
                    "targetStorageMode": "DirectQuery",
                },
            ],
            "reports": [
                {"id": "rep-1", "name": "Finance Dashboard", "datasetId": "ds-a"},
                {"id": "rep-2", "name": "Legacy Report", "datasetId": "ds-deleted"},
            ],
        }
    ]
}


def test_flatten_scan_result_normalizes_fields():
    items = flatten_scan_result(_SCAN_RESULT)
    by_id = {i["id"]: i for i in items}

    ds_a = by_id["ds-a"]
    assert ds_a["itemType"] == "Dataset"
    assert ds_a["endorsement"] == "Certified"
    assert ds_a["hasSensitivityLabel"] is True
    assert ds_a["hasRls"] is True
    assert ds_a["storageMode"] == "Import"

    ds_b = by_id["ds-b"]
    assert ds_b["endorsement"] == "None"
    assert ds_b["hasSensitivityLabel"] is False
    assert ds_b["hasRls"] is False

    # rep-1 resolves to an existing dataset; rep-2 points at a deleted one.
    assert by_id["rep-1"]["orphaned"] is False
    assert by_id["rep-2"]["orphaned"] is True


def test_flatten_empty_is_empty():
    assert flatten_scan_result({}) == []
    assert flatten_scan_result({"workspaces": []}) == []


class _FakeClient:
    """Records POSTs and replays a canned scanStatus/scanResult sequence (no sleeping)."""

    def __init__(self, result):
        self._result = result
        self.posts = []

    def post(self, url, params=None, json=None):
        self.posts.append({"url": url, "params": params, "json": json})
        return {"id": "scan-123", "status": "NotStarted"}

    def get(self, url, params=None):
        if "scanStatus" in url:
            return {"status": "Succeeded"}
        if "scanResult" in url:
            return self._result
        return {}


def test_collect_scanner_items_runs_async_flow():
    client = _FakeClient(_SCAN_RESULT)
    items = collect_scanner_items(client, ["ws-1"], poll_interval=0, max_polls=3)
    assert len(items) == 4
    assert client.posts[0]["json"] == {"workspaces": ["ws-1"]}
    assert client.posts[0]["params"]["getArtifactUsers"] == "true"


def test_collect_scanner_items_batches_over_100_workspaces():
    client = _FakeClient({"workspaces": []})
    ws_ids = [f"ws-{n}" for n in range(250)]
    collect_scanner_items(client, ws_ids, poll_interval=0, max_polls=1)
    # 250 workspaces -> 3 batches (100 + 100 + 50).
    assert len(client.posts) == 3
    assert [len(p["json"]["workspaces"]) for p in client.posts] == [100, 100, 50]


def test_collect_scanner_items_empty_workspaces():
    client = _FakeClient(_SCAN_RESULT)
    assert collect_scanner_items(client, []) == []
    assert client.posts == []
