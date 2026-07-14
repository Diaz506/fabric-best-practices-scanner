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

Traditional governance reviews rely on lengthy manual questionnaires. This package instead
**collects the answers from your tenant automatically** and evaluates them against a curated
best-practice catalog — so you can run it yourself, on a schedule, and trend your posture
over time in Power BI.

## How it works

> **Findings, not a score.** Rather than compressing governance into a single 1–5 maturity
> number, the scanner reports discrete, actionable findings — each tied to a specific best
> practice and the evidence behind it.

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
2. **Confidence-scored applicability** — each rule scores 0–100% applicability from signals.
3. **Impact-gated flagging** — ambiguous *high-impact* rules are surfaced + flagged; ambiguous
   low/medium-impact rules are dropped to keep the report clean.
4. **AI only for rationale** — Azure OpenAI (optional) expands narrative; it never decides status.

## Coverage
All seven governance dimensions are included:
**Tenant Settings & Administration**, **Capacity & Cost Governance**, **Workspace Governance**,
**Roles & Access**, **Domains & Data Mesh**, **Data Security**, and **Monitoring & Deployment**.
Add or tune rules by editing the YAML files in `src/fabric_bps/catalog/`.

---

## Prerequisites

- Python 3.9+
- A way to call the **read-only admin APIs**, one of:
  - Run inside a **Fabric notebook** as a user with **Fabric Administrator / Power BI Service Administrator**, or
  - A **service principal** added to the group allowed by the tenant setting
    **"Service principals can use read-only admin APIs"** (enable it once as a tenant admin).

## Deployment & manual effort

There is **no manual data entry and no questionnaire** — every finding is observed from the
admin APIs. The only work is one-time setup:

| Step | Effort | When |
|---|---|---|
| Deploy notebook + semantic model + report into the workspace | **Automated** (Jumpstart install / Git integration) | Once |
| Provide a read-only admin identity | **~0 min** if you already have an admin login; **~10 min** to configure a service principal | Once |
| Attach the notebook to a Lakehouse | **~1 min** | Once |
| Run the scan | **1 click** (or scheduled) | Each run |
| Bind the semantic model to the Lakehouse | **~2 min** (auto-binds via Git integration) | Once |
| Finish report visuals | **Optional ~10–15 min** (measures prebuilt; drag-and-drop recipe) | Once |

**Minimum happy path (admin identity): ~5 minutes** — attach Lakehouse → run → bind the model.
Full breakdown in [`docs/deployment.md`](docs/deployment.md).

## Install

```bash
# From PyPI (once published)
pip install fabric-best-practices-scanner
pip install "fabric-best-practices-scanner[sp,fabric,ai]"   # + service-principal auth, parquet fallback, AI rationale
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
Findings are written to a Lakehouse Delta table (`governance_findings`), appended per run
with `run_id` + `timestamp`. A semantic model + report template over that table gives a
governance report with trend over time. See [`powerbi/README.md`](powerbi/README.md).

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
- Add the Scanner API collector for deeper per-item lineage, endorsement, and label coverage.
- Add collectors for sensitivity labels, activity events, and Git integration.
- Publish to PyPI; list in the Fabric Jumpstart catalog.
