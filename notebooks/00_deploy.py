# %% [markdown]
# # Fabric Best Practices Scanner — One-click Deploy
#
# Run **all cells** to stand up the scanner in *this* workspace end to end:
#
# 1. Provisions the **Lakehouse** that stores findings (creates it if missing).
# 2. Installs the scanner package.
# 3. Runs the scan and writes `governance_findings` to the Lakehouse.
# 4. Deploys the **Direct Lake semantic model** (with prebuilt measures) bound to it.
#
# You do **not** need to create or attach a Lakehouse by hand — this notebook does it.
#
# **Prerequisites**
# - Run as a user with **Fabric Administrator / Power BI Service Administrator**, OR
#   configure a service principal (see `00-setup.md`).
# - Pre-publish only: upload the wheel from `dist/` to *any* Lakehouse's Files, or set
#   `WHEEL_PATH` below to an accessible path. Once on PyPI this step goes away.

# %%
# Parameters — safe to leave as defaults.
LAKEHOUSE_NAME = "GovernanceScanner"      # created in this workspace if it doesn't exist
DATASET_NAME = "FabricGovernance"          # semantic model name
TABLE_NAME = "governance_findings"

# Pre-publish install source (uploaded wheel). Set to None once installing from PyPI.
WHEEL_PATH = "/lakehouse/default/Files/fabric_best_practices_scanner-0.1.0-py3-none-any.whl"

# %%
# Install the package. Pre-publish: from the uploaded wheel. Published: from PyPI.
if WHEEL_PATH:
    %pip install -q {WHEEL_PATH}
else:
    %pip install -q fabric-best-practices-scanner

# %%
# 1) Provision the findings Lakehouse (idempotent — reused if it already exists).
from fabric_bps.report import provision_lakehouse

lh = provision_lakehouse(name=LAKEHOUSE_NAME)
print(("Created" if lh["created"] else "Reusing"), "Lakehouse:", lh["name"], lh["id"])

# %%
# 2) Run the scan and write findings straight to the provisioned Lakehouse.
from fabric_bps import scan
from fabric_bps.collectors import fabric_notebook_token_provider

result = scan(
    fabric_notebook_token_provider(),
    dimensions=None,                 # None = all catalog areas
    write="lakehouse",
    table=TABLE_NAME,
    spark=spark,                     # provided by the Fabric notebook runtime
    lakehouse_abfss=lh["abfss"],     # write by path — no default-attach needed
    ai_rationale=False,              # True if AZURE_OPENAI_* env vars are set
)

print("Archetype:", result["context"]["archetype"])
print("Findings:", len(result["findings"]))
print("Output:", result.get("output"))
if result.get("collection_errors"):
    print("Collection errors:", result["collection_errors"])

# %%
# Quick summary by status.
from collections import Counter

for status, n in Counter(f.status.value for f in result["findings"]).most_common():
    print(f"{status:22} {n}")

# %%
# 3) Deploy the Direct Lake semantic model bound to the provisioned Lakehouse.
from fabric_bps.report import deploy_semantic_model

dataset = deploy_semantic_model(
    dataset=DATASET_NAME,
    lakehouse=lh["id"],              # bind to the Lakehouse we just provisioned
    workspace=lh["workspace_id"],
    table=TABLE_NAME,
    refresh=True,
)
print("Semantic model deployed:", dataset)

# %%
# Optional: also create a bound starter report (non-fatal if unavailable).
from fabric_bps.report import deploy_report

print(deploy_report(dataset=DATASET_NAME, report=DATASET_NAME, workspace=lh["workspace_id"]))

# %% [markdown]
# ## Done
#
# Findings are in the **`governance_findings`** table of the `GovernanceScanner` Lakehouse,
# and the **`FabricGovernance`** semantic model is ready. Build visuals using the recipe in
# `powerbi/README.md`, or open the shipped `.pbip` report.
#
# Re-run any time to refresh — findings append (with run id + timestamp) so the report can
# trend posture over successive runs.
