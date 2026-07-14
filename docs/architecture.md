# Architecture

## Pipeline
```
Collectors ──► Signals ──► Archetype classifier ──► Context
                                   │
Rule catalog (YAML) ───────────────┼──► Evaluation engine ──► Findings
                                   │        (applicability + impact-gated flagging)
                                   ▼
                       Checks registry (Python)
                                   │
                                   ▼
          AI rationale (optional) ─► Writers ─► Lakehouse Delta table ─► Power BI report
```

## Components
- **Collectors** (`collectors/`) — call Fabric/Power BI read-only admin APIs and normalize
  responses into a `Signals` object. Auth via notebook identity or service principal.
- **Signals** (`signals.py`) — the only thing the engine reads. Decouples logic from I/O,
  making the engine testable offline.
- **Rule catalog** (`catalog/*.yaml`) — best practices as **declarative data**: dimension,
  WAF pillar, impact/severity, applicability conditions, an `evaluate` check reference,
  recommendation, rationale, references. Language-neutral; the web app can reuse it later.
- **Checks** (`checks.py`) — reusable Python primitives that implement the actual evidence
  logic; referenced by name from the catalog. Returns `(Status, evidence)`.
- **Archetype classifier** (`archetype.py`) — one explainable, auto-derived context decision.
- **Engine** (`engine.py`) — per rule: applicability confidence → evaluate → impact-gated
  flagging → `Finding`.
- **Writers** (`writers/`) — Lakehouse Delta (primary) and JSON (secondary).
- **AI** (`ai.py`) — optional Azure OpenAI rationale enrichment; never decides status.

## Design decisions (locked)
- **Best-practices rules engine, not a maturity score.**
- **Near-zero manual input** — auto-collect from admin APIs; residual process items surface
  as `verify-applicability` / `insufficient-data` (optional review, not required input).
- **Applicability policy** — archetype + confidence + impact-gated flagging; AI for rationale only.
- **Delivery** — Python module/notebook inside the customer's Fabric workspace (Jumpstart-native).
- **Primary output** — Power BI governance report over a Lakehouse findings table (trend per run).
- **Catalog is data, not code** — content translated from the web app's `recommendations.ts`.

## Known tradeoffs
- **Setting-name drift** — tenant `settingName`s vary by release/tenant; unknown settings
  return `insufficient-data` (safe) rather than a wrong answer.
- **Catalog duplication** — content currently lives here and in the web app; long-term the
  web app should consume this shared catalog for a single source of truth.
- **Process/people practices** — not API-observable; represented honestly as verify/insufficient.
