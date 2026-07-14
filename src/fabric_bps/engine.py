"""Evaluation engine.

For each rule:
  1. Compute applicability confidence from the customer context (archetype + signals).
  2. If explicitly not-applicable -> omit.
  3. Run the evidence check -> raw status.
  4. Impact-gated verify-flagging (the locked applicability policy):
       - confidence >= APPLY_THRESHOLD          -> rule applies; keep evaluate status
       - confidence <  APPLY_THRESHOLD, impact high  -> surface + flag verify-applicability
       - confidence <  APPLY_THRESHOLD, otherwise    -> silently drop (keep report clean)
  5. Emit a Finding with confidence, evidence, archetype, run_id, timestamp.
"""
from __future__ import annotations

import datetime
import uuid

from .checks import get_check
from .models import Finding, Impact, Rule, Status

APPLY_THRESHOLD = 60


def _resolve(dotted: str, context: dict):
    cur = context
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _matches(cond: dict, context: dict) -> bool:
    for key, expected in cond.items():
        actual = _resolve(key, context)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def applicability_confidence(rule: Rule, context: dict):
    """Return (confidence, is_not_applicable)."""
    app = rule.applicability
    for cond in app.not_applicable_when:
        if _matches(cond, context):
            return 0, True
    conf = app.base_confidence
    for boost in app.boosts:
        if _matches(boost.when, context):
            conf = max(conf, boost.confidence)
    return conf, False


def evaluate(signals, context: dict, rules, run_id: str = None):
    run_id = run_id or uuid.uuid4().hex[:12]
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    archetype = context.get("archetype")
    findings = []

    for rule in rules:
        conf, not_applicable = applicability_confidence(rule, context)
        if not_applicable:
            continue

        if rule.evaluate is None:
            status, evidence = Status.INSUFFICIENT_DATA, {"reason": "no evaluate spec"}
        else:
            fn = get_check(rule.evaluate.check)
            status, evidence = fn(signals, rule.evaluate.params)

        # Impact-gated flagging on ambiguous applicability.
        if conf < APPLY_THRESHOLD:
            if rule.impact == Impact.HIGH:
                status = Status.VERIFY_APPLICABILITY
                evidence = {
                    **evidence,
                    "applicability_confidence": conf,
                    "reason": "ambiguous applicability; high impact -> flagged for verification",
                }
            else:
                continue  # silently drop low/medium-impact ambiguous rules

        findings.append(
            Finding(
                rule_id=rule.id,
                dimension=rule.dimension,
                title=rule.title,
                waf_pillar=rule.waf_pillar,
                status=status,
                impact=rule.impact,
                severity=rule.severity,
                applicability_confidence=conf,
                recommendation=rule.recommendation,
                rationale=rule.rationale,
                references=rule.references,
                effort=rule.effort,
                evidence=evidence,
                archetype=archetype,
                run_id=run_id,
                timestamp=ts,
            )
        )
    return findings
