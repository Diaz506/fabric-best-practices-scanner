# Setup — Prerequisites for the Fabric Best Practices Scanner

The scanner reads your tenant's configuration through the **read-only admin APIs**. You need
one of the two identities below.

## Option A — Run in a Fabric notebook as an admin (simplest)
1. Sign in as a user with **Fabric Administrator** or **Power BI Service Administrator**.
2. Import `00_deploy.ipynb` (one-click: provisions the Lakehouse, scans, and deploys the model)
   and **run all cells**. Prefer to attach your own Lakehouse? Use `01_run_scanner.py` instead.
3. `fabric_notebook_token_provider()` acquires the token via `notebookutils` automatically.

> The notebook installs the package from the **public GitHub repo**
> (`%pip install "git+https://github.com/Diaz506/fabric-best-practices-scanner.git"`) —
> no wheel upload needed.

## Option B — Service principal (headless / scheduled)
One-time tenant-admin configuration:
1. Register an Entra app (service principal) and create a client secret.
2. Create a security group (e.g. *Governance Automation SPs*) and add the SP.
3. In the **Fabric/Power BI Admin portal → Tenant settings**, enable
   **"Service principals can use read-only admin APIs"** and scope it to that group.
   Also enable **"Service principals can access read-only admin APIs metadata"** if present.

Then:
```python
from fabric_bps import scan
from fabric_bps.collectors import service_principal_token_provider

tp = service_principal_token_provider(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
result = scan(tp, write="json")
```

## Content Governance (Scanner API) — one extra tenant setting
The **Content Governance** rules (dataset endorsement, sensitivity labels, row-level security,
storage mode, orphaned reports) read per-artifact metadata from the **Scanner API**. Enable:

1. **Fabric/Power BI Admin portal → Tenant settings → Admin API settings →
   "Enhance admin APIs responses with detailed metadata"** — required for these rules.
2. *(Optional)* **"Enhance admin APIs responses with detailed metadata of users"** — adds
   per-artifact user lists for future item-ownership rules.

Without the *detailed metadata* setting, content rules report `insufficient-data` and the rest
of the scan is unaffected. To skip the Scanner API entirely, call `scan(..., scanner=False)`.
Changes to these settings can take a few minutes to propagate across the tenant.

## Optional — AI rationale (Azure OpenAI)
Set these environment variables to enable narrative enrichment (`ai_rationale=True`):
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT` (default `gpt-4o`)

AI never decides status/applicability — it only expands human-readable rationale.

## Permissions summary
| Data | API | Role/permission |
|---|---|---|
| Tenant settings | `GET /admin/tenantsettings` (Fabric) | Fabric/Power BI admin or scoped SP |
| Capacities | `GET /admin/capacities` (Power BI) | Fabric/Power BI admin or scoped SP |
| Workspaces + roles | `GET /admin/groups?$expand=users` (Power BI) | Fabric/Power BI admin or scoped SP |
| Domains | `GET /admin/domains` (Fabric) | Fabric/Power BI admin or scoped SP |
| Content metadata (endorsement, labels, RLS, orphaned items) | Scanner API: `POST /admin/workspaces/getInfo` → `GET /admin/workspaces/scanStatus/{id}` → `GET /admin/workspaces/scanResult/{id}` (Power BI) | Admin/SP **plus** the *"Enhance admin APIs responses with detailed metadata"* tenant setting |
