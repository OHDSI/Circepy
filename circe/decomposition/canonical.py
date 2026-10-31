"""Content-addressed canonicalisation for shared cohort-set execution.

In a Circe v1 cohort definition, concept-set identifiers are *cohort local*:
two cohorts in the same definition set can use different ids for the same
concept set, or the same id for different content.  Shared execution compares
pipeline checkpoints across cohorts, so identifiers have to be rewritten to
run-global, content-addressed ids first.

Two identifiers are produced:

* :class:`ConceptSetCanonicalizer` assigns one id per distinct concept-set
  *content* (items, exclusions, descendant/mapped flags), registers the
  normalised concept sets for the shared ``(codeset_id, concept_id)`` table, and
  rewrites every ``codeset_id`` reference in a copy of the expression.
* :func:`semantic_expression_key` canonicalises a standalone expression by
  content-sorted concept-set ids, so two definitions that differ only in local
  ids (or concept display metadata) compare equal.

The canonicalisation never mutates the caller's expression.  Original
definitions are preserved for output; only the execution path uses the
rewritten copy.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from typing import Any

from pydantic import BaseModel

from ..cohortdefinition import CohortExpression
from ..execution.normalize.cohort import (
    NormalizedConceptSet,
    _extract_codesets,
)
from ..vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

__all__ = [
    "ConceptSetCanonicalizer",
    "concept_set_content_key",
    "semantic_expression_key",
    "stable_digest",
]


def _semantic_items(expression: ConceptSetExpression | None) -> list[tuple[int, bool, bool, bool]]:
    """Return the concept-set items that affect SQL, ignoring display metadata."""
    if expression is None:
        return []

    items: list[tuple[int, bool, bool, bool]] = []

    if expression.concept is not None and expression.concept.concept_id is not None:
        items.append(
            (
                int(expression.concept.concept_id),
                bool(expression.is_excluded),
                bool(expression.include_descendants),
                bool(expression.include_mapped),
            )
        )

    for item in expression.items or []:
        if item is None or item.concept is None or item.concept.concept_id is None:
            continue
        items.append(
            (
                int(item.concept.concept_id),
                bool(item.is_excluded),
                bool(item.include_descendants),
                bool(item.include_mapped),
            )
        )

    return items


def concept_set_content_key(expression: ConceptSetExpression | None) -> str:
    """Return a stable hash of the SQL-relevant content of a concept set."""
    payload = json.dumps(_semantic_items(expression), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stable_digest(value: Any) -> str:
    """Hash an arbitrary nested value deterministically (order-sensitive)."""
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, BaseModel):
        return _jsonable(value.model_dump(mode="json", by_alias=True))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, (int, float, str)):
        return value
    return str(value)


def _strip_concept(concept: Concept | None) -> Concept | None:
    if concept is None or concept.concept_id is None:
        return None
    return Concept(concept_id=int(concept.concept_id))


def _strip_expression(expression: ConceptSetExpression | None) -> ConceptSetExpression | None:
    if expression is None:
        return None
    return ConceptSetExpression(
        concept=_strip_concept(expression.concept),
        is_excluded=bool(expression.is_excluded),
        include_mapped=bool(expression.include_mapped),
        include_descendants=bool(expression.include_descendants),
        items=[
            ConceptSetItem(
                concept=_strip_concept(item.concept),
                is_excluded=bool(item.is_excluded),
                include_mapped=bool(item.include_mapped),
                include_descendants=bool(item.include_descendants),
            )
            for item in expression.items or []
            if item is not None
        ],
    )


def _rewrite_codeset_ids(node: Any, mapping: Mapping[int, int]) -> None:
    """Rewrite every ``codeset_id`` reference in a pydantic model tree in place."""
    if isinstance(node, BaseModel):
        for field_name in type(node).model_fields:
            value = getattr(node, field_name)
            if field_name == "codeset_id" and isinstance(value, int) and not isinstance(value, bool):
                replacement = mapping.get(value)
                if replacement is not None and replacement != value:
                    setattr(node, field_name, replacement)
            elif isinstance(value, (BaseModel, list, tuple, dict)):
                _rewrite_codeset_ids(value, mapping)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _rewrite_codeset_ids(item, mapping)
    elif isinstance(node, dict):
        for item in node.values():
            _rewrite_codeset_ids(item, mapping)


class ConceptSetCanonicalizer:
    """Assign run-global ids to concept sets by content.

    The canonicaliser is stateful across one cohort-set run: the first time a
    piece of content is registered it receives the next sequential id; later
    occurrences (even from another cohort with a different local id) reuse it.
    """

    def __init__(self) -> None:
        self._id_by_key: dict[str, int] = {}
        self._key_by_id: dict[int, str] = {}
        self._concept_sets: dict[int, NormalizedConceptSet] = {}

    @property
    def concept_sets(self) -> dict[int, NormalizedConceptSet]:
        """Canonical concept sets registered so far, keyed by canonical id."""
        return dict(self._concept_sets)

    def __len__(self) -> int:
        return len(self._id_by_key)

    def register(self, concept_set: ConceptSet) -> int:
        """Register *concept_set* and return its canonical id."""
        key = concept_set_content_key(concept_set.expression)
        existing = self._id_by_key.get(key)
        if existing is not None:
            return existing

        canonical_id = len(self._id_by_key) + 1
        self._id_by_key[key] = canonical_id
        self._key_by_id[canonical_id] = key

        normalized = _extract_codesets([ConceptSet(id=canonical_id, expression=concept_set.expression)])
        self._concept_sets[canonical_id] = normalized.get(
            canonical_id,
            NormalizedConceptSet(set_id=canonical_id, items=()),
        )
        return canonical_id

    def register_expression(self, expression: CohortExpression) -> None:
        """Register every concept set in *expression* (idempotent)."""
        for concept_set in expression.concept_sets or []:
            if concept_set is None:
                continue
            self.register(concept_set)

    def canonicalize(self, expression: CohortExpression) -> CohortExpression:
        """Return a copy of *expression* using canonical concept-set ids."""
        canonical = expression.model_copy(deep=True)

        mapping: dict[int, int] = {}
        rebuilt: list[ConceptSet] = []
        seen: set[int] = set()

        for concept_set in canonical.concept_sets or []:
            if concept_set is None:
                continue
            canonical_id = self.register(concept_set)
            mapping[int(concept_set.id)] = canonical_id
            if canonical_id in seen:
                continue
            seen.add(canonical_id)
            concept_set.id = canonical_id
            rebuilt.append(concept_set)

        canonical.concept_sets = rebuilt
        _rewrite_codeset_ids(canonical, mapping)
        return canonical


def semantic_expression_key(expression: CohortExpression, *, include_title: bool = True) -> str:
    """Return a canonical semantic key for a cohort definition.

    Concept sets are deduplicated and ordered by content, ids are reassigned by
    that order, display metadata is stripped, and the remaining expression is
    hashed.  Definitions that are logically identical but use different local
    concept-set ids therefore produce the same key.
    """
    canonical = expression.model_copy(deep=True)

    keys = [concept_set_content_key(cs.expression) for cs in canonical.concept_sets or []]
    unique_keys = sorted(set(keys))
    id_by_key = {key: index + 1 for index, key in enumerate(unique_keys)}

    mapping: dict[int, int] = {}
    rebuilt: list[ConceptSet] = []
    for concept_set, key in zip(canonical.concept_sets or [], keys, strict=False):
        canonical_id = id_by_key[key]
        mapping[int(concept_set.id)] = canonical_id
        if canonical_id in {int(existing.id) for existing in rebuilt}:
            continue
        rebuilt.append(
            ConceptSet(
                id=canonical_id,
                expression=_strip_expression(concept_set.expression),
            )
        )

    canonical.concept_sets = rebuilt
    _rewrite_codeset_ids(canonical, mapping)

    data = canonical.model_dump(by_alias=True, mode="json", exclude_none=True)
    if not include_title:
        data.pop("Title", None)
        data.pop("title", None)
    return stable_digest(data)
