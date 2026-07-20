# Deployment & manual effort

This is a self-service Jumpstart solution: it deploys into **your** Fabric workspace and reads
your tenant's configuration through the read-only admin APIs. There is **no manual data entry** —
every finding comes from what the APIs report. The only manual work is one-time setup
(identity + wiring), summarized below.

## Manual effort at a glance
| # | Step | Effort | Who | When | Can it be skipped/automated? |
|---|------|--------|-----|------|------------------------------|
| 1 | Deploy the solution (notebook + semantic model + report) into the workspace | **Automated** | — | Once | Yes — done by the Jumpstart install / Git integration |
| 2 | Provide a read-only admin identity | **Manual, ~5–10 min** | Tenant admin | Once | Path A is free if you already have an admin login; Path B (SP) is the ~10-min part |
| 3 | Create the findings Lakehouse | **Automated** | — | Once | Yes — `00_deploy.py` creates it and writes by path (no manual attach) |
| 4 | Run the scan + auto-deploy the semantic model | **1 click / automated** | Analyst | Each run | The notebook provisions the Lakehouse, scans, and creates a Lakehouse-bound Direct Lake model with the measures — **no connection placeholders to fill in** |
| 5 | Finish the report visuals | **Optional, ~10–15 min** | Analyst | Once | Optional — measures are prebuilt; drag-and-drop recipe provided |
| 6 | Schedule re-runs for trend | **Optional, ~2 min** | Analyst | Once | Optional |
| 7 | Enable AI rationale | **Optional** | Analyst | Once | Optional — set Azure OpenAI env vars |

**Bottom line:** if you already have a Fabric/Power BI admin login, the minimum path is
**import `00_deploy.py` → run all cells (~2–3 minutes)** — it provisions the Lakehouse, runs
the scan, and creates and binds the semantic model automatically. The service-principal path
(step 2, Path B) adds a one-time ~10 minutes but gives you a headless, schedulable setup.

## Step 2 — the only real "it depends" choice: which identity?

### Path A — run as an admin (simplest, zero SP setup)
No extra configuration. You just need to sign in (or run the notebook) as a user who already has
**Fabric Administrator** or **Power BI Service Administrator**. Manual effort here is **zero**.

### Path B — service principal (headless / scheduled)
One-time tenant-admin configuration (~10 min):
1. Register an Entra app + client secret.
2. Create a security group (e.g. *Governance Automation SPs*) and add the app.
3. Admin portal → Tenant settings → enable **"Service principals can use read-only admin APIs"**
   and scope it to that group.

Choose Path B only if you want the scan to run unattended on a schedule.

## What is *not* manual
- **No data entry** — the scanner does not ask you anything about your tenant; it observes it
  via the admin APIs.
- **No per-rule tuning required** — applicability is derived automatically (archetype +
  confidence + impact gating). You *can* tune rules by editing the YAML catalog, but you don't
  have to.
- **No report modeling from scratch** — the DirectLake semantic model and all measures ship
  prebuilt; you only bind the connection (step 5).

## The 2-minute happy path (admin identity)
1. Import `notebooks/00_deploy.py` as a notebook. (No Lakehouse to create or attach — the
   notebook provisions it for you.)
2. **Run all cells.** It installs the package, **creates the `GovernanceScanner` Lakehouse**,
   scans, writes `governance_findings`, and **auto-deploys a Lakehouse-bound Direct Lake
   semantic model** (with all measures) — no connection placeholders to fill in.
3. Build the report visuals from the prebuilt measures using the recipe in
   [`powerbi/README.md`](../powerbi/README.md), or open the shipped `.pbip`.

That's the whole deployment. Re-run the notebook (or schedule it) to build the posture trend.

> Prefer to attach an existing Lakehouse and run manually? Use `notebooks/01_run_scanner.py`
> instead — same scan, but you attach the Lakehouse yourself.

## Authoring path (no Fabric compute)
Prefer to work in Power BI Desktop instead of the notebook auto-deploy? Open
`powerbi/FabricGovernance.pbip`, set the two connection placeholders in `expressions.tmdl`,
and refresh. The auto-deploy path above avoids this entirely.
