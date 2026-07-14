# Power BI — Governance report

The scanner writes findings to a Lakehouse Delta table (`governance_findings`), one row per
`(run_id, rule_id)`, appended each run. Build a semantic model + report over that table.

## Findings table schema
| Column | Type | Notes |
|---|---|---|
| run_id | string | Groups one scan; use for latest-run and trend |
| timestamp | string (ISO) | Convert to datetime in the model |
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

## Suggested report pages
1. **Overview** — donut of status split, cards for gaps / verify / adherence %,
   status by dimension (stacked bar), status by WAF pillar.
2. **Gaps & priorities** — table of `status = gap` sorted by impact/severity, with
   recommendation + references.
3. **Verify** — the `verify-applicability` bucket on its own page (the review queue).
4. **Trend** — line chart of gap count / adherence % over `run_id`/`timestamp`.
5. **Evidence detail** — drill-through per rule showing the `evidence` JSON.

## Suggested measures (DAX sketch)
```DAX
Latest Run = CALCULATE(MAX('findings'[run_id]), ALL('findings'))
Gaps = CALCULATE(COUNTROWS('findings'), 'findings'[status] = "gap")
Adherence % =
DIVIDE(
    CALCULATE(COUNTROWS('findings'), 'findings'[status] = "adhered"),
    CALCULATE(COUNTROWS('findings'), 'findings'[status] IN {"adhered","gap"})
)
```

## TODO
Ship a prebuilt `.pbip` project (report + semantic model bound to the Lakehouse) so
the report is deployed as part of the Jumpstart install.
