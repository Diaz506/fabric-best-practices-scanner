"""Core data models for the Fabric Best Practices Scanner.

The scanner is a *contextual best-practices rules engine* that reports evidence-backed findings.
Each best practice is a Rule with an applicability condition + an evidence check.
The engine emits Findings (one per applicable rule) with a Status.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Status(str, Enum):
    """Outcome of evaluating a rule against collected evidence."""

    ADHERED = "adhered"
    GAP = "gap"
    NOT_APPLICABLE = "not-applicable"
    VERIFY_APPLICABILITY = "verify-applicability"
    INSUFFICIENT_DATA = "insufficient-data"


class Impact(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EvaluateSpec:
    """Declarative reference to a registered check primitive + its params."""

    check: str
    params: dict = field(default_factory=dict)


@dataclass
class ApplicabilityBoost:
    when: dict
    confidence: int


@dataclass
class Applicability:
    """Controls whether a rule applies to a given customer context.

    base_confidence: default applicability confidence (0-100).
    boosts: raise confidence when a context condition matches.
    not_applicable_when: hard-exclude the rule when a condition matches.
    """

    base_confidence: int = 70
    boosts: list[ApplicabilityBoost] = field(default_factory=list)
    not_applicable_when: list[dict] = field(default_factory=list)


@dataclass
class Rule:
    id: str
    dimension: str
    title: str
    waf_pillar: Optional[str] = None
    impact: Impact = Impact.MEDIUM
    severity: Severity = Severity.MEDIUM
    applicability: Applicability = field(default_factory=Applicability)
    evaluate: Optional[EvaluateSpec] = None
    recommendation: str = ""
    rationale: str = ""
    references: list[str] = field(default_factory=list)
    effort: str = "medium"


@dataclass
class Finding:
    rule_id: str
    dimension: str
    title: str
    waf_pillar: Optional[str]
    status: Status
    impact: Impact
    severity: Severity
    applicability_confidence: int
    recommendation: str
    rationale: str
    references: list[str]
    effort: str
    evidence: dict = field(default_factory=dict)
    archetype: Optional[str] = None
    run_id: Optional[str] = None
    timestamp: Optional[str] = None

    def to_row(self) -> dict:
        """Flat, tabular representation for the Lakehouse findings table / Power BI."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "rule_id": self.rule_id,
            "dimension": self.dimension,
            "title": self.title,
            "waf_pillar": self.waf_pillar,
            "status": self.status.value,
            "impact": self.impact.value,
            "severity": self.severity.value,
            "applicability_confidence": self.applicability_confidence,
            "recommendation": self.recommendation,
            "rationale": self.rationale,
            "references": ", ".join(self.references),
            "reference_url": self.references[0] if self.references else "",
            "effort": self.effort,
            "evidence": json.dumps(self.evidence, ensure_ascii=False),
            "archetype": self.archetype,
        }
