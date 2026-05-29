"""
ConceptPredicateItem model.

A predicate item uses declarative expressions (vocabulary filters, hierarchy
traversal, string matching, set operations) that resolve to concept_ids
against OMOP vocabulary tables.

GUARD RAIL: This is a Python-only extension. There is no Java CIRCE-BE equivalent.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .predicate_expressions import PredicateExpression


class ConceptPredicateItem(BaseModel):
    type: Literal["predicate_item"] = "predicate_item"
    name: str | None = None
    is_excluded: bool = Field(default=False, alias="isExcluded")
    expression: PredicateExpression

    model_config = ConfigDict(populate_by_name=True)
