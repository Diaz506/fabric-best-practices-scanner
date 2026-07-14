"""Parse rule dicts (from YAML) into Rule dataclasses."""
from __future__ import annotations

from ..models import (
    Applicability,
    ApplicabilityBoost,
    EvaluateSpec,
    Impact,
    Rule,
    Severity,
)


def rule_from_dict(d: dict) -> Rule:
    ev = d.get("evaluate")
    evaluate = EvaluateSpec(check=ev["check"], params=ev.get("params", {})) if ev else None

    app_d = d.get("applicability", {}) or {}
    applicability = Applicability(
        base_confidence=int(app_d.get("base_confidence", 70)),
        boosts=[
            ApplicabilityBoost(when=b["when"], confidence=int(b["confidence"]))
            for b in app_d.get("boosts", [])
        ],
        not_applicable_when=app_d.get("not_applicable_when", []),
    )

    return Rule(
        id=d["id"],
        dimension=d["dimension"],
        title=d["title"],
        waf_pillar=d.get("waf_pillar"),
        impact=Impact(d.get("impact", "medium")),
        severity=Severity(d.get("severity", "medium")),
        applicability=applicability,
        evaluate=evaluate,
        recommendation=d.get("recommendation", ""),
        rationale=d.get("rationale", ""),
        references=d.get("references", []) or [],
        effort=d.get("effort", "medium"),
    )
