"""
Vocabulary Module

This module contains classes for managing concepts, concept sets, and concept set expressions.
It mirrors the Java CIRCE-BE vocabulary package structure.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .concept import Concept, ConceptExpressionItem, ConceptSet, ConceptSetExpression, ConceptSetItem

# Note: ConceptSetExpressionQueryBuilder is not exported here to avoid circular imports
# Import it directly: from circe.vocabulary.concept_set_expression_query_builder import ConceptSetExpressionQueryBuilder

__all__ = [
    "Concept",
    "ConceptSet",
    "ConceptSetExpression",
    "ConceptSetItem",  # Backward compatibility alias
    "ConceptExpressionItem",
]
