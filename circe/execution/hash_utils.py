"""Deterministic hashing helpers for cohort orchestration."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List

from ..io import ExpressionInput, load_expression
from .cohort_definition_set import CohortDefinitionSet


def canonicalize_expression(expression: ExpressionInput) -> Dict[str, Any]:
    """Return canonical JSON-compatible payload for hash computation."""
    cohort_expression = load_expression(expression)
    return cohort_expression.model_dump(by_alias=True, exclude_none=True)


def compute_definition_hash(expression: ExpressionInput) -> str:
    """Compute stable SHA-256 hash for one cohort definition."""
    canonical_payload = canonicalize_expression(expression)
    canonical_json = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _canonical_set_payload(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        items,
        key=lambda value: (
            str(value["cohort_id"]),
            value.get("name") or "",
            value["definition_hash"],
        ),
    )


def compute_set_hash(definition_set: CohortDefinitionSet) -> str:
    """Compute stable SHA-256 hash for a cohort definition set."""
    members = [
        {
            "cohort_id": member.cohort_id,
            "name": member.name,
            "definition_hash": compute_definition_hash(member.expression),
        }
        for member in definition_set.cohorts
    ]
    canonical_payload = {
        "set_id": definition_set.set_id,
        "set_name": definition_set.set_name,
        "version": definition_set.version,
        "description": definition_set.description,
        "tags": sorted(definition_set.tags or []),
        "members": _canonical_set_payload(members),
    }
    canonical_json = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

