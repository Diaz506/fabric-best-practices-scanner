"""Best-practice rule catalog loader.

Rules live as declarative YAML data files in this folder (one per dimension), so the
catalog is language-neutral and maintainable. Add a new dimension by dropping in a new
*.yaml file.
"""
from __future__ import annotations

import glob
import os

import yaml

from ..models import Rule
from .schema import rule_from_dict

CATALOG_DIR = os.path.dirname(__file__)


def load_catalog(dimensions=None) -> list:
    rules: list[Rule] = []
    for path in sorted(glob.glob(os.path.join(CATALOG_DIR, "*.yaml"))):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for rd in data.get("rules", []):
            rule = rule_from_dict(rd)
            if dimensions and rule.dimension not in dimensions:
                continue
            rules.append(rule)
    return rules
