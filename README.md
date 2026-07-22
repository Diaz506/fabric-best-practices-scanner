# Fabric Best Practices Scanner

> Scan a Microsoft Fabric tenant against a **contextual best-practices catalog** and produce
> prioritized, evidence-backed governance **findings** — with **near-zero manual input**.
> Built to run self-service inside your own Fabric workspace, aligned to the
> **Fabric Jumpstart** methodology.

Every best practice is a *rule* with an *applicability condition* + an *evidence check*. The
engine reads your tenant's actual state from the Fabric/Power BI **read-only admin APIs**,
decides which practices apply to *you*, and reports where you adhere, where there are gaps,
and what it couldn't verify automatically.

> ⚠️ Not an official Microsoft tool. Advisory only — validate against your org's
> requirements and Microsoft's official documentation.

---

## Why this exists

This package collects your tenant's configuration from the **read-only admin APIs**
automatically and evaluates it against a curated best-practice catalog — so you can run it
yourself, on a schedule, and trend your posture over time in Power BI, with **near-zero
manual input**.

## How it works

> **Actionable findings.** The scanner reports discrete findings — each tied to a specific
> best practice, a clear status, and the evidence behind it — so you know exactly what to
> act on.

```
collect (admin APIs)  ->  classify (archetype)  ->  evaluate (rules + evidence)
      ->  impact-gated flagging  ->  findings  ->  Lakehouse table  ->  Power BI report
```

### Finding statuses
| Status | Meaning |
|---|---|
| `adhered` | Evidence shows the practice is followed |
| `gap` | Evidence shows the practice is not followed |
| `verify-applicability` | Auto-collection was ambiguous / partial — confirm (5-second review) |
| `not-applicable` | The practice does not apply to your environment |
| `insufficient-data` | No API signal available to judge — confirm manually |

### Applicability policy (why not every best practice appears)
1. **Archetype classification** — one explainable, auto-derived call ("what matters for this tenant").
2. **Confidence-rated applicability** — each rule gets a 0–100% applicability confidence from signals.
3. **Impact-gated flagging** — ambiguous *high-impact* rules are surfaced + flagged; ambiguous
   low/medium-impact rules are dropped to keep the report clean.
4. **AI only for rationale** — Azure OpenAI (optional) expands narrative; it never decides status.

## Coverage
The catalog checks eight areas of Fabric governance:
**Tenant Settings & Administration**, **Capacity & Cost**, **Workspace Governance**,
**Roles & Access**, **Domains & Data Mesh**, **Data Security**, **Monitoring & Deployment**,
and **Content Governance** (endorsement, sensitivity labels, row-level security, and orphaned
items — from the Scanner API metadata).
These are how this catalog is organized, not an official Microsoft taxonomy.
Add or tune rules by editing the YAML files in `src/fabric_bps/catalog/`.

---

## Prerequisites

- Python 3.9+
- **An admin identity** to call the read-only admin APIs, one of:
  - Run inside a **Fabric notebook** as a user with the **Fabric Administrator** or **Power BI
    Service Administrator** role, or
  - A **service principal** added to the security group allowed by the *"Service principals can
    use read-only admin APIs"* tenant setting (headless / scheduled runs).

### Required & optional tenant settings

Set these once in the **Fabric/Power BI Admin portal → Tenant settings** (mostly under the
**Admin API settings** group). Each row notes what it unlocks and what happens without it.

| Tenant setting | Needed for | Required? | Without it |
|---|---|---|---|
| **Fabric Administrator / Power BI Service Administrator** role (or an SP in the allowed group) | All admin API calls (tenant settings, capacities, workspaces, domains) | **Required** | The scan cannot read tenant state at all |
| **Service principals can use read-only admin APIs** | Running headless via a service principal (Path B) | Required **only for the SP path** | Use an admin user instead (Path A) |
| **Enhance admin APIs responses with detailed metadata** | **Content Governance** rules — dataset endorsement, sensitivity labels, row-level security, storage mode, orphaned reports (Scanner API) | Required for content rules | Content rules report `insufficient-data`; the rest of the scan is unaffected |
| **Enhance admin APIs responses with detailed metadata of users** | Per-artifact user lists (future item-ownership rules) | Optional | Item-level user metadata is omitted; no current rule fails |

> Scanner API note: content rules run only when the *detailed metadata* setting is on. To skip
> the Scanner API entirely (e.g. before enabling the setting), call `scan(..., scanner=False)`.

## Deployment & manual effort

There is **no manual data entry** — every finding is observed from the
admin APIs. The only work is one-time setup:

| Step | Effort | When |
|---|---|---|
| Deploy notebook + semantic model + report into the workspace | **Automated** (Jumpstart install / Git integration) | Once |
| Provide a read-only admin identity | **~0 min** if you already have an admin login; **~10 min** to configure a service principal | Once |
| Create the findings Lakehouse | **Automated** — `00_deploy.ipynb` creates it for you | Once |
| Run the scan + auto-deploy the model | **1 click** (creates a Lakehouse-bound Direct Lake model with measures) | Each run |
| Report visuals | **Automated** — `deploy_report` builds a populated report (cards + charts + findings table) | Once |

**Minimum happy path (admin identity): ~2–3 minutes** — import `notebooks/00_deploy.ipynb` and
run all cells; it provisions the Lakehouse, runs the scan, and creates and binds the semantic
model automatically. Full breakdown in [`docs/deployment.md`](docs/deployment.md).

## Quickstart (one-click, in Fabric)

1. Sign in as a user with **Fabric Administrator / Power BI Service Administrator**.
2. Import [`notebooks/00_deploy.ipynb`](notebooks/00_deploy.ipynb) into your workspace.
3. **Run all cells.** It provisions the `GovernanceScanner` Lakehouse, scans your tenant,
   writes `governance_findings` and `governance_inventory`, and deploys the `FabricGovernance`
   semantic model and report (findings + an admin control center: inventory and orphans).

> The notebook installs the package from this **public GitHub repo**
> (`%pip install "git+https://github.com/Diaz506/fabric-best-practices-scanner.git"`) —
> no wheel upload and no Lakehouse attach required.

Prefer to attach an existing Lakehouse and run manually? Use
[`notebooks/01_run_scanner.py`](notebooks/01_run_scanner.py) — same scan, you attach the
Lakehouse yourself.

## Install

Runs in a Fabric notebook — install straight from this **public GitHub repo** (no wheel
upload, no Lakehouse attach):

```bash
%pip install "git+https://github.com/Diaz506/fabric-best-practices-scanner.git"
# with extras:  %pip install "fabric-best-practices-scanner[sp,fabric,ai] @ git+https://github.com/Diaz506/fabric-best-practices-scanner.git"
```

### From source
```bash
pip install -e ".[sp,fabric,ai]"
```

## Usage

### In a Fabric notebook (primary path)
```python
from fabric_bps import scan
from fabric_bps.collectors import fabric_notebook_token_provider

result = scan(
    fabric_notebook_token_provider(),
    write="lakehouse",         # append to the findings Delta table
    table="governance_findings",
    spark=spark,               # the notebook's Spark session
    ai_rationale=False,        # set True if Azure OpenAI env vars are configured
)
print(result["context"]["archetype"], len(result["findings"]), "findings")
```

### Headless (service principal)
```python
from fabric_bps import scan
from fabric_bps.collectors import service_principal_token_provider

tp = service_principal_token_provider(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
result = scan(tp, write="json")
```

### Offline / testing (no tenant)
```python
import json
from fabric_bps import scan_from_signals

signals = json.load(open("tests/sample_signals.json"))
result = scan_from_signals(signals)
for f in result["findings"]:
    print(f.status.value, f.rule_id)
```

## Output → Power BI
Findings are written to a Lakehouse Delta table (`governance_findings`) and a resource
inventory to `governance_inventory`, both appended per run with `run_id` + `timestamp`. A
semantic model + report template over those tables gives a governance report (Overview,
Findings Detail) plus an admin control center (Resource Inventory, Orphans & Unused) with
trend over time. See [`powerbi/README.md`](powerbi/README.md).

## Develop / test
```bash
pip install -e ".[dev]"
pytest -q
```

## Project layout
```
src/fabric_bps/
  models.py         # Rule / Finding / Status data models
  signals.py        # normalized tenant signals
  checks.py         # reusable evidence-check primitives (the logic)
  catalog/*.yaml    # best-practice rules (the data)
  archetype.py      # context classifier
  engine.py         # applicability + impact-gated evaluation
  collectors/       # Fabric/Power BI admin API collectors + auth
  writers/          # JSON + Lakehouse Delta writers
  ai.py             # optional Azure OpenAI rationale
  run.py            # scan() / scan_from_signals() entry points
notebooks/          # setup + run notebooks (Jumpstart entry points)
powerbi/            # semantic model + report template
```

## Roadmap
- Add collectors for sensitivity-label taxonomy, activity events, and Git integration.
- Publish as a listed solution in the Fabric Jumpstart catalog.
