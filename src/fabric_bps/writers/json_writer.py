"""Write findings to a JSON file (secondary / programmatic output)."""
from __future__ import annotations

import json


def write_json(findings, path: str = "governance_findings.json") -> str:
    rows = [f.to_row() for f in findings]
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(rows, fp, indent=2, ensure_ascii=False)
    return path
