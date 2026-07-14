# Power BI — Governance report

The scanner writes findings to a Lakehouse Delta table (`governance_findings`), one row per
`(run_id, rule_id)`, appended each run. This folder ships a **DirectLake semantic model**
(the model comes first) and a **starter report** bound to it, as a `.pbip` project so both
are versioned as plain text and deploy via Fabric Git integration.

## What's in this folder
```
FabricGovernance.pbip                     <- open this in Power BI Desktop (Fabric-enabled)
FabricGovernance.SemanticModel/           <- DirectLake model over governance_findings (TMDL)
  definition/expressions.tmdl             <- Lakehouse SQL endpoint connection (edit placeholders)
  definition/tables/governance_findings.tmdl  <- columns + all governance measures
FabricGovernance.Report/                  <- starter report (2 named pages) bound to the model
```
The semantic model is the reusable asset: schema + measures. The report pages ship empty on
purpose so the project opens cleanly everywhere; assemble the visuals in minutes using the
recipe below (all measures are pre-built).

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

