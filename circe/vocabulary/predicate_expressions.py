"""
Predicate expression types for concept set predicate items.

This module defines the expression tree types used by ConceptPredicateItem
to resolve sets of concept_ids against OMOP vocabulary tables.

GUARD RAIL: This is a Python-only extension. There is no Java CIRCE-BE equivalent.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel


class SetOperation(str, Enum):
    UNION = "UNION"
    INTERSECT = "INTERSECT"
    MINUS = "MINUS"


class VocabularyScope(BaseModel):
    type: Literal["vocabulary_scope"] = "vocabulary_scope"
    vocabulary_id: str
    domain_id: str | None = None
    concept_class_id: str | None = None
    standard_concept: Literal["S", "C", "any"] = "S"


class HierarchyDescend(BaseModel):
    type: Literal["hierarchy_descend"] = "hierarchy_descend"
    ancestor_concept_id: int
    include_ancestor: bool = True
    max_depth: int | None = None


class StringFilter(BaseModel):
    type: Literal["string_filter"] = "string_filter"
    pattern: str
    match_type: Literal["LIKE", "ILIKE"] = "ILIKE"
    scope: VocabularyScope | None = None


class SetOperationNode(BaseModel):
    type: Literal["set_operation"] = "set_operation"
    operation: SetOperation
    operands: list[PredicateExpression]


PredicateExpression = Union[
    VocabularyScope,
    HierarchyDescend,
    StringFilter,
    SetOperationNode,
]

SetOperationNode.model_rebuild()
