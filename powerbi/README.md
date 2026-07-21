# Power BI — Governance report

The scanner writes findings to a Lakehouse Delta table (`governance_findings`), one row per
`(run_id, rule_id)`, appended each run. This folder ships a **DirectLake semantic model**
(the model comes first) and a **populated report** bound to it, as a `.pbip` project so both
are versioned as plain text and deploy via Fabric Git integration.

The one-click notebook's `deploy_report` step builds this same report automatically in your
workspace (Governance Overview, Findings Detail, Resource Inventory, and Orphans & Unused
pages), so you normally don't touch this folder. The recipe below is here if you want to
rebuild or customize the visuals by hand.

## What's in this folder
```
FabricGovernance.pbip                     <- open this in Power BI Desktop (Fabric-enabled)
FabricGovernance.SemanticModel/           <- DirectLake model over the Lakehouse tables (TMDL)
  definition/expressions.tmdl             <- Lakehouse SQL endpoint connection (edit placeholders)
  definition/tables/governance_findings.tmdl   <- findings columns + all governance measures
  definition/tables/governance_inventory.tmdl  <- inventory columns + admin control-center measures
FabricGovernance.Report/                  <- report (4 named pages, populated) bound to the model
```
The semantic model is the reusable asset: schema + measures. The report ships populated (and
`deploy_report` rebuilds it in your workspace); the recipe below documents how the visuals are
assembled from the pre-built measures if you want to customize them.

## Bind it to your Lakehouse (one-time)
1. In Fabric, open your Lakehouse → **Settings → SQL analytics endpoint** and copy the
   **Server** (connection string) and the **Lakehouse name**.
2. Edit `FabricGovernance.SemanticModel/definition/expressions.tmdl` and replace the two
   `REPLACE-WITH-...` placeholders.
3. Open `FabricGovernance.pbip` in Power BI Desktop, or push the folder into a Fabric
   workspace via **Git integration** (Workspace → Settings → Git integration), which rebinds
   the connection automatically.

## Findings table schema
| Column | Type | Notes |
|---|---|---|
| run_id | string | Groups one scan; use for latest-run and trend |
| timestamp | string (ISO) | Sorts chronologically as text |
| rule_id | string | Stable best-practice id |
| dimension | string | e.g. tenant-settings, capacity-cost |
| title | string | Human-readable best practice |
| waf_pillar | string | Reliability/Security/Cost/OpEx/Performance |
| status | string | adhered / gap / verify-applicability / not-applicable / insufficient-data |
| impact | string | low / medium / high |
| severity | string | info / low / medium / high / critical |
| applicability_confidence | int | 0–100 |
| recommendation | string | What to do |
| rationale | string | Why it matters (AI-enriched if enabled) |
| references | string | Doc links |
| effort | string | low / medium / high |
| evidence | string (JSON) | What the scanner observed |
| archetype | string | Classified tenant archetype |

## Prebuilt measures (in the model)
Current-posture (scoped to the most recent scan):
`Latest Run ID`, `Findings (Latest Run)`, `Adhered (Latest Run)`, `Gaps (Latest Run)`,
`Verify Applicability (Latest Run)`, `Insufficient Data (Latest Run)`, `Evaluated (Latest Run)`,
`Adherence Rate (Latest Run)`, `High-Impact Gaps (Latest Run)`.

Trend (put `run_id` or `timestamp` on the axis):
`Adhered (This Run)`, `Gaps (This Run)`, `Adherence Rate (This Run)`.

> `Adherence Rate` is the share of *clearly evaluated* rules (adhered ÷ (adhered + gaps)).
> It deliberately excludes `verify-applicability` and `insufficient-data` — it is a simple
> adherence percentage over the rules with a clear verdict, not an overall rating.

## Build the report (drag-and-drop recipe)
**Page 1 — Governance Overview**
- Cards: `Adherence Rate (Latest Run)`, `Gaps (Latest Run)`, `High-Impact Gaps (Latest Run)`,
  `Verify Applicability (Latest Run)`.
- Stacked bar: Axis = `dimension`, Values = `Findings (Latest Run)`, Legend = `status`.
- Clustered bar: Axis = `waf_pillar`, Values = `Gaps (Latest Run)`.
- Line chart: Axis = `timestamp`, Values = `Adherence Rate (This Run)` (posture trend).

**Page 2 — Findings Detail**
- Table: `dimension`, `title`, `status`, `impact`, `effort`, `recommendation`, `references`.
- Page-level filter `status = gap` for the priority queue; duplicate for a
  `verify-applicability` review page if desired.
- Add `evidence` as a tooltip/drill-through to expose what the scanner observed.

## Admin control center (inventory)
The scanner also writes a resource inventory to the Lakehouse Delta table
`governance_inventory` (one row per workspace, capacity, and domain, appended each run) with
orphan/unused flags. The model exposes control-center measures: `Latest Inventory Run ID`,
`Resources (Latest Run)`, `Workspaces (Latest Run)`, `Capacities (Latest Run)`,
`Domains (Latest Run)`, `Orphaned Resources (Latest Run)`.

### Inventory table schema
| Column | Type | Notes |
|---|---|---|
| run_id | string | Groups one snapshot; use for latest-run and trend |
| timestamp | string (ISO) | Sorts chronologically as text |
| resource_type | string | Workspace / Personal Workspace / Capacity / Domain |
| resource_id | string | Fabric resource id |
| name | string | Display name |
| state | string | e.g. Active, Deleted, Paused |
| sku | string | Capacity SKU (capacities) |
| region | string | Capacity region (capacities) |
| on_dedicated_capacity | string | Yes / No (workspaces) |
| capacity_name | string | Assigned capacity (workspaces) |
| domain_name | string | Assigned domain |
| admin_count | int | Number of admins |
| user_count | int | Number of role assignments |
| is_orphan | string | Yes / No |
| orphan_reasons | string | Comma-separated flags (e.g. no-workspaces-assigned) |

**Page 3 — Resource Inventory**
- Cards: `Resources (Latest Run)`, `Workspaces (Latest Run)`, `Capacities (Latest Run)`,
  `Domains (Latest Run)`, `Orphaned Resources (Latest Run)`.
- Matrix: Rows = `resource_type`, Columns = `state`, Values = `Resources (Latest Run)`.
- Table: `resource_type`, `name`, `state`, `sku`, `region`, `capacity_name`, `domain_name`,
  `admin_count`, `user_count`, `is_orphan`, sliced by `resource_type`.

**Page 4 — Orphans & Unused**
- Slicers: `is_orphan` and `resource_type` to focus cleanup.
- Table: `name`, `resource_type`, `state`, `orphan_reasons`, `capacity_name`, `domain_name`,
  `admin_count`, `user_count`.

