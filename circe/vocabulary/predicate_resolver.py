"""
Resolver for predicate expressions.

Executes compiled SQL against a database connection and returns resolved concept_ids.

GUARD RAIL: This is a Python-only extension. There is no Java CIRCE-BE equivalent.
"""

from __future__ import annotations

from typing import Protocol

from circe.vocabulary.concept import ConceptExpressionItem, ConceptSetExpression
from circe.vocabulary.predicate_expressions import PredicateExpression
from circe.vocabulary.predicate_item import ConceptPredicateItem
from circe.vocabulary.predicate_sql_compiler import PredicateSQLCompiler


class VocabularyConnection(Protocol):
    """Abstract database connection for vocabulary queries."""

    def execute(self, sql: str) -> list[tuple]: ...


class ConceptSetResolver:
    """Resolves concept sets (including predicate items) to sets of concept_ids."""

    def __init__(self, connection: VocabularyConnection, compiler: PredicateSQLCompiler):
        self.connection = connection
        self.compiler = compiler

    def resolve_expression(self, expr: PredicateExpression) -> set[int]:
        """Resolve a single predicate expression to concept_ids."""
        sql = self.compiler.compile_expression(expr)
        return self._execute(sql)

    def resolve_item(self, item: ConceptExpressionItem | ConceptPredicateItem) -> set[int]:
        """Resolve a single item (concept or predicate) to concept_ids."""
        if isinstance(item, ConceptExpressionItem):
            return self._resolve_concept_item(item)
        if isinstance(item, ConceptPredicateItem):
            return self.resolve_expression(item.expression)
        raise TypeError(f"Unknown item type: {type(item).__name__}")

    def resolve(self, concept_set: ConceptSetExpression) -> set[int]:
        """Resolve full concept set to final set of concept_ids.

        Logic: union(included_items) - union(excluded_items)
        """
        included: set[int] = set()
        excluded: set[int] = set()

        if not concept_set.items:
            return included

        for item in concept_set.items:
            resolved = self.resolve_item(item)
            if item.is_excluded:
                excluded |= resolved
            else:
                included |= resolved

        return included - excluded

    def _resolve_concept_item(self, item: ConceptExpressionItem) -> set[int]:
        """Resolve a traditional ConceptExpressionItem to concept_ids."""
        concept_id = item.concept.concept_id
        if concept_id is None:
            return set()

        result: set[int] = set()

        sql = self.compiler.compile_concept_id_list([concept_id])
        result |= self._execute(sql)

        if item.include_descendants:
            from circe.vocabulary.predicate_expressions import HierarchyDescend

            descend = HierarchyDescend.model_validate(
                {
                    "ancestor_concept_id": concept_id,
                    "include_ancestor": False,
                }
            )
            sql = self.compiler.compile_expression(descend)
            result |= self._execute(sql)

        if item.include_mapped:
            mapped_sql = (
                f"SELECT DISTINCT cr.concept_id_1 AS concept_id "
                f"FROM ({self.compiler.compile_concept_id_list([concept_id])}) c "
                f"JOIN @vocabulary_database_schema.concept_relationship cr "
                f"ON c.concept_id = cr.concept_id_2 "
                f"AND cr.relationship_id = 'Maps to' "
                f"AND cr.invalid_reason IS NULL"
            )
            result |= self._execute(mapped_sql)

        return result

    def _execute(self, sql: str) -> set[int]:
        result: set[int] = set()
        rows = self.connection.execute(sql)
        for row in rows:
            result.add(row[0])
        return result
