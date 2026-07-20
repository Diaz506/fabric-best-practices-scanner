# %% [markdown]
# # Fabric Best Practices Scanner — Run
#
# Runs the governance best-practices scan inside your Fabric workspace and writes findings
# to a Lakehouse Delta table for the Power BI report.
#
# **Prerequisites**
# - Attach this notebook to a Lakehouse (for the `governance_findings` table).
# - Run as a user with **Fabric Administrator / Power BI Service Administrator**, OR
#   configure a service principal (see `00-setup.md`).

# %%
# Install the package + deploy extra from the public GitHub repo (no wheel upload needed).
# The [deploy] extra pulls semantic-link-labs (not preinstalled in the Fabric runtime).
%pip install -q "fabric-best-practices-scanner[deploy] @ git+https://github.com/Diaz506/fabric-best-practices-scanner.git"

# %%
from fabric_bps import scan
from fabric_bps.collectors import fabric_notebook_token_provider

result = scan(
    fabric_notebook_token_provider(),
    dimensions=None,               # None = all catalog dimensions
    write="lakehouse",
    table="governance_findings",
    spark=spark,                   # provided by the Fabric notebook runtime
    ai_rationale=False,            # True if AZURE_OPENAI_* env vars are set
)

print("Archetype:", result["context"]["archetype"])
print("Findings:", len(result["findings"]))
print("Output:", result.get("output"))

# %%
# Quick in-notebook summary by status.
from collections import Counter

counts = Counter(f.status.value for f in result["findings"])
for status, n in counts.most_common():
    print(f"{status:22} {n}")

# %%
# Show the gaps and items to verify.
for f in result["findings"]:
    if f.status.value in ("gap", "verify-applicability"):
        print(f"[{f.status.value}] {f.title}")
        print(f"    -> {f.recommendation.strip()}")

# %% [markdown]
# ## Auto-deploy the report model (optional, one click)
#
# Creates a **Direct Lake semantic model** bound to *this* Lakehouse (no connection
# placeholders) and adds the prebuilt governance measures. Re-running is safe: the model
# is refreshed and only missing measures are added. `deploy_report` then creates a populated
# report (overview cards + charts and a findings table) bound to the model.
#
# Requires `semantic-link-labs` — installed by the `[deploy]` extra in the first cell
# (it is not preinstalled in the Fabric runtime).

# %%
from fabric_bps.report import deploy_semantic_model

dataset = deploy_semantic_model(
    dataset="FabricGovernance",
    lakehouse=None,   # None = the Lakehouse attached to this notebook
    workspace=None,   # None = this notebook's workspace
    refresh=True,
)
print("Semantic model deployed:", dataset)

# %%
# Create the populated report (cards + charts + findings table) bound to the model.
# Non-fatal: if report creation is unavailable, open the shipped `.pbip` report instead.
from fabric_bps.report import deploy_report

print(deploy_report(dataset="FabricGovernance", report="FabricGovernance"))
