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
    match_type: Literal["LIKE", "ILIKE", "REGEX"] = "ILIKE"
    scope: VocabularyScope | None = None


class ConceptCodeFilter(BaseModel):
    type: Literal["concept_code_filter"] = "concept_code_filter"
    codes: list[str]
    match_type: Literal["exact", "LIKE", "ILIKE", "REGEX"] = "exact"
    scope: VocabularyScope | None = None


class ConceptSynonymFilter(BaseModel):
    type: Literal["concept_synonym_filter"] = "concept_synonym_filter"
    pattern: str
    match_type: Literal["LIKE", "ILIKE", "REGEX"] = "ILIKE"
    scope: VocabularyScope | None = None


class HierarchyAscend(BaseModel):
    type: Literal["hierarchy_ascend"] = "hierarchy_ascend"
    descendant_concept_id: int
    include_descendant: bool = True
    max_depth: int | None = None


class ImmediateChildren(BaseModel):
    type: Literal["immediate_children"] = "immediate_children"
    ancestor_concept_id: int


class ConceptIdRange(BaseModel):
    type: Literal["concept_id_range"] = "concept_id_range"
    min_id: int | None = None
    max_id: int | None = None
    scope: VocabularyScope | None = None


class ConceptDateFilter(BaseModel):
    type: Literal["concept_date_filter"] = "concept_date_filter"
    valid_on_date: str | None = None
    valid_start_date: str | None = None
    valid_end_date: str | None = None
    scope: VocabularyScope | None = None


class SetOperationNode(BaseModel):
    type: Literal["set_operation"] = "set_operation"
    operation: SetOperation
    operands: list[PredicateExpression]


PredicateExpression = Union[
    VocabularyScope,
    HierarchyDescend,
    StringFilter,
    ConceptCodeFilter,
    ConceptSynonymFilter,
    HierarchyAscend,
    ImmediateChildren,
    ConceptIdRange,
    ConceptDateFilter,
    SetOperationNode,
]

SetOperationNode.model_rebuild()
