"""Write findings to a Fabric Lakehouse Delta table (primary output).

In a Fabric notebook, pass the Spark session; findings are appended (with run_id +
timestamp) so the Power BI report can trend governance posture over successive runs.

Two Lakehouse targets are supported:
  - Default (attached) Lakehouse: ``saveAsTable(table)`` writes to the notebook's
    attached Lakehouse metastore.
  - Explicit Lakehouse (``lakehouse_abfss`` set): writes the Delta table straight to
    ``{lakehouse_abfss}/Tables/{table}`` via ``save()``. This lets the one-click
    deploy notebook write to a Lakehouse it just provisioned, with no manual attach.

Outside Fabric, falls back to parquet (if pandas is available) then JSON, so the
writer is import-safe and testable offline.
"""
from __future__ import annotations

import json


def write_lakehouse(
    findings,
    table: str = "governance_findings",
    spark=None,
    lakehouse_abfss: str = None,
) -> str:
    rows = [f.to_row() for f in findings]

    if spark is not None:
        df = spark.createDataFrame(rows)
        writer = df.write.format("delta").mode("append").option("mergeSchema", "true")
        if lakehouse_abfss:
            path = f"{lakehouse_abfss.rstrip('/')}/Tables/{table}"
            writer.save(path)
            return f"delta:{path} ({len(rows)} rows appended)"
        writer.saveAsTable(table)
        return f"delta:{table} ({len(rows)} rows appended)"

    try:
        import pandas as pd

        out = f"{table}.parquet"
        pd.DataFrame(rows).to_parquet(out, index=False)
        return out
    except Exception:
        out = f"{table}.json"
        with open(out, "w", encoding="utf-8") as fp:
            json.dump(rows, fp, indent=2, ensure_ascii=False)
        return out
