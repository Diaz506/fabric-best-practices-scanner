"""Provision the Fabric items the scanner needs (one-click deploy).

Creates the Lakehouse that stores ``governance_findings`` if it does not already
exist, and returns the identifiers a Fabric notebook needs to write to it *without*
attaching it as the default Lakehouse. This is what lets the deploy notebook run
end to end from a single click: provision -> scan -> deploy report.

Runs inside a Fabric notebook (uses ``notebookutils``). Import-safe offline: the
Fabric-only imports happen inside the function.
"""
from __future__ import annotations

ONELAKE_DFS = "onelake.dfs.fabric.microsoft.com"


def _current_workspace_id() -> str:
    import notebookutils  # available in the Fabric runtime

    return notebookutils.runtime.context["currentWorkspaceId"]


def provision_lakehouse(
    name: str = "GovernanceScanner",
    description: str = "Fabric Best Practices Scanner findings store.",
    workspace_id: str = None,
) -> dict:
    """Create the findings Lakehouse if missing and return its coordinates.

    Returns a dict with ``name``, ``id``, ``workspace_id``, ``abfss`` (the OneLake
    root of the Lakehouse) and ``created`` (True if it was created by this call).
    Pass ``abfss`` to ``scan(..., lakehouse_abfss=...)`` and ``id`` to
    ``deploy_semantic_model(lakehouse=...)``.
    """
    import notebookutils  # available in the Fabric runtime

    workspace_id = workspace_id or _current_workspace_id()

    created = False
    try:
        artifact = notebookutils.lakehouse.get(name, workspace_id)
    except Exception:  # noqa: BLE001 - not found -> create it
        artifact = notebookutils.lakehouse.create(name, description, {}, workspace_id)
        created = True

    lakehouse_id = artifact["id"] if isinstance(artifact, dict) else artifact.id
    abfss = f"abfss://{workspace_id}@{ONELAKE_DFS}/{lakehouse_id}"

    return {
        "name": name,
        "id": lakehouse_id,
        "workspace_id": workspace_id,
        "abfss": abfss,
        "created": created,
    }
