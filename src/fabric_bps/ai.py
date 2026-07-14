"""Optional AI rationale enrichment (Azure OpenAI).

AI is used ONLY to expand human-readable rationale/narrative for findings — never to
decide applicability or status (keeps the engine deterministic and auditable). Fully
optional: if Azure OpenAI is not configured, findings pass through unchanged.
"""
from __future__ import annotations

import os


def is_configured() -> bool:
    return bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"))


def enrich_rationale(findings, only_statuses=("gap", "verify-applicability")):
    """Best-effort narrative enrichment. Returns findings unchanged on any failure."""
    if not is_configured():
        return findings
    try:
        from openai import AzureOpenAI
    except Exception:
        return findings

    try:
        client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
        )
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    except Exception:
        return findings

    for f in findings:
        if f.status.value not in only_statuses:
            continue
        try:
            prompt = (
                f"Best practice: {f.title}\n"
                f"Status: {f.status.value}\n"
                f"Evidence: {f.evidence}\n"
                f"Base recommendation: {f.recommendation}\n\n"
                "Write 2-3 sentences of business-oriented rationale explaining why this "
                "matters and the risk of not addressing it. Be specific and concise."
            )
            resp = client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=180,
            )
            f.rationale = resp.choices[0].message.content.strip()
        except Exception:
            continue  # leave the rule-based rationale in place
    return findings
