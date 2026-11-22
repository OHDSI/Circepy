"""Parity between circe.capr and R's Capr 3.0.0.

The fixtures in ``fixtures/`` are the JSON that R's Capr produces for the same
cohorts. Output is compared *semantically*, after normalising differences that
are not meaningful or that stem from pre-existing circepy behaviour:

- ``cdmVersionRange`` is dropped by the shared models on round-trip.
- Models always serialize ``False`` defaults (``First``, ``ConditionTypeExclude``,
  ``RestrictVisit``, ...) that Capr omits.
- Concept metadata that Capr writes as empty strings is omitted here.
- Capr writes inclusion rules with lowercase keys; CIRCE uses PascalCase.
- Domain criteria serialize gender as ``gender`` (known pre-existing bug,
  tracked separately); CIRCE-BE uses ``Gender``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from circe import capr

from .reference_cohorts import REFERENCE_COHORTS

FIXTURES = Path(__file__).parent / "fixtures"

_DROPPED_KEYS = {"cdmVersionRange"}
_FALSE_DEFAULTS = {
    "First",
    "ConditionTypeExclude",
    "DeathTypeExclude",
    "DrugTypeExclude",
    "MeasurementTypeExclude",
    "RestrictVisit",
    "IgnoreObservationPeriod",
    "IsDistinct",
}
_EMPTY_CONCEPT_STRINGS = {
    "CONCEPT_NAME",
    "STANDARD_CONCEPT",
    "STANDARD_CONCEPT_CAPTION",
    "INVALID_REASON",
    "INVALID_REASON_CAPTION",
    "CONCEPT_CODE",
    "DOMAIN_ID",
    "VOCABULARY_ID",
    "CONCEPT_CLASS_ID",
}
_RULE_KEYS = {"name": "Name", "expression": "Expression"}
_KEY_CASE = {"gender": "Gender"}
_CONCEPT_SET_EXPRESSION_DEFAULTS = {"isExcluded", "includeMapped", "includeDescendants"}


def _normalise(node: Any, *, in_concept_set_expression: bool = False) -> Any:
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        local_expression = node.get("expression") is not None and "items" in node.get("expression", {})
        for key, value in node.items():
            if key in _DROPPED_KEYS:
                continue
            if key in _FALSE_DEFAULTS and value is False:
                continue
            if key in _EMPTY_CONCEPT_STRINGS and value in ("", None):
                continue
            if in_concept_set_expression and key in _CONCEPT_SET_EXPRESSION_DEFAULTS and value is False:
                continue
            out[_KEY_CASE.get(key, key)] = _normalise(value, in_concept_set_expression=local_expression)
        return out
    if isinstance(node, list):
        return [_normalise(item, in_concept_set_expression=in_concept_set_expression) for item in node]
    return node


def _normalise_inclusion_rule_keys(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            key: (
                [{_RULE_KEYS.get(k, k): v for k, v in rule.items()} for rule in value]
                if key == "InclusionRules" and isinstance(value, list)
                else _normalise_inclusion_rule_keys(value)
            )
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_normalise_inclusion_rule_keys(item) for item in node]
    return node


def _load(name: str) -> Any:
    payload = json.loads((FIXTURES / f"{name}.json").read_text())
    return _normalise_inclusion_rule_keys(_normalise(payload))


def _actual(builder) -> Any:
    payload = json.loads(capr.to_cohort_json(builder()))
    return _normalise_inclusion_rule_keys(_normalise(payload))


@pytest.mark.parametrize("name", sorted(REFERENCE_COHORTS))
def test_matches_r_capr(name: str) -> None:
    """circe.capr produces the same definition as R's Capr."""
    assert _actual(REFERENCE_COHORTS[name]) == _load(name)
