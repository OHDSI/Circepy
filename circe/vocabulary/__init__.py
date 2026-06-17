"""
Vocabulary Module

This module contains classes for managing concepts, concept sets, and concept set expressions.
It mirrors the Java CIRCE-BE vocabulary package structure.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .concept import Concept, ConceptExpressionItem, ConceptSet, ConceptSetExpression, ConceptSetItem
from .predicate_compat import ConceptSetCompat, ManifestGenerator, ResolutionManifest
from .predicate_expressions import (
    ConceptCodeFilter,
    ConceptDateFilter,
    ConceptIdRange,
    ConceptSynonymFilter,
    HierarchyAscend,
    HierarchyDescend,
    ImmediateChildren,
    PredicateExpression,
    SetOperation,
    SetOperationNode,
    StringFilter,
    VocabularyScope,
)
from .predicate_item import ConceptPredicateItem
from .predicate_resolver import ConceptSetResolver
from .predicate_sql_compiler import PredicateSQLCompiler
from .predicate_validator import PredicateValidator, ValidationWarning

# Note: ConceptSetExpressionQueryBuilder is not exported here to avoid circular imports
# Import it directly: from circe.vocabulary.concept_set_expression_query_builder import ConceptSetExpressionQueryBuilder

__all__ = [
    "Concept",
    "ConceptSet",
    "ConceptSetExpression",
    "ConceptSetItem",
    "ConceptExpressionItem",
    "ConceptPredicateItem",
    "PredicateExpression",
    "VocabularyScope",
    "HierarchyDescend",
    "HierarchyAscend",
    "ImmediateChildren",
    "StringFilter",
    "ConceptCodeFilter",
    "ConceptSynonymFilter",
    "ConceptIdRange",
    "ConceptDateFilter",
    "SetOperationNode",
    "SetOperation",
    "PredicateSQLCompiler",
    "ConceptSetResolver",
    "PredicateValidator",
    "ValidationWarning",
    "ConceptSetCompat",
    "ResolutionManifest",
    "ManifestGenerator",
]
