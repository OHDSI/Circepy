"""
SQL compiler for predicate expressions.

Translates predicate expression trees into SQL SELECT queries against
standard OMOP vocabulary tables (concept, concept_ancestor).

GUARD RAIL: This is a Python-only extension. There is no Java CIRCE-BE equivalent.
"""

from __future__ import annotations

from circe.vocabulary.predicate_expressions import (
    HierarchyDescend,
    PredicateExpression,
    SetOperation,
    SetOperationNode,
    StringFilter,
    VocabularyScope,
)

SCHEMA_PLACEHOLDER = "@vocabulary_database_schema"


class PredicateSQLCompiler:
    """Compiles predicate expressions to SQL SELECT queries returning concept_id."""

    def compile_expression(self, expr: PredicateExpression) -> str:
        """Compile a predicate expression to a SQL SELECT returning concept_id."""
        if isinstance(expr, VocabularyScope):
            return self._compile_vocabulary_scope(expr)
        if isinstance(expr, HierarchyDescend):
            return self._compile_hierarchy_descend(expr)
        if isinstance(expr, StringFilter):
            return self._compile_string_filter(expr)
        if isinstance(expr, SetOperationNode):
            return self._compile_set_operation(expr)
        raise TypeError(f"Unknown expression type: {type(expr).__name__}")

    def compile_concept_id_list(self, concept_ids: list[int], column: str = "concept_id") -> str:
        """Compile a simple list of concept IDs to a SELECT."""
        ids = ", ".join(str(cid) for cid in concept_ids)
        return f"SELECT {column} FROM {SCHEMA_PLACEHOLDER}.CONCEPT WHERE {column} IN ({ids})"

    def _compile_vocabulary_scope(self, expr: VocabularyScope) -> str:
        conditions = [f"vocabulary_id = '{expr.vocabulary_id}'"]
        if expr.domain_id:
            conditions.append(f"domain_id = '{expr.domain_id}'")
        if expr.concept_class_id:
            conditions.append(f"concept_class_id = '{expr.concept_class_id}'")
        if expr.standard_concept == "any":
            pass
        else:
            conditions.append(f"standard_concept = '{expr.standard_concept}'")
        conditions.append("invalid_reason IS NULL")
        where = " AND ".join(conditions)
        return f"SELECT concept_id FROM {SCHEMA_PLACEHOLDER}.CONCEPT WHERE {where}"

    def _compile_hierarchy_descend(self, expr: HierarchyDescend) -> str:
        ancestor_id = expr.ancestor_concept_id
        ancestor_condition = f"ancestor_concept_id = {ancestor_id}"
        if expr.max_depth is not None:
            ancestor_condition += f" AND min_levels_of_separation <= {expr.max_depth}"
        depth_filter = ""
        if expr.include_ancestor:
            depth_filter = " AND min_levels_of_separation >= 0"
        else:
            depth_filter = " AND min_levels_of_separation >= 1"
        return (
            f"SELECT ca.descendant_concept_id AS concept_id "
            f"FROM {SCHEMA_PLACEHOLDER}.CONCEPT_ANCESTOR ca "
            f"JOIN {SCHEMA_PLACEHOLDER}.CONCEPT c ON ca.descendant_concept_id = c.concept_id "
            f"WHERE {ancestor_condition}{depth_filter} AND c.invalid_reason IS NULL"
        )

    def _compile_string_filter(self, expr: StringFilter) -> str:
        like_op = "ILIKE" if expr.match_type == "ILIKE" else "LIKE"
        conditions = [f"concept_name {like_op} '{expr.pattern}'"]
        if expr.scope:
            if expr.scope.vocabulary_id:
                conditions.append(f"vocabulary_id = '{expr.scope.vocabulary_id}'")
            if expr.scope.domain_id:
                conditions.append(f"domain_id = '{expr.scope.domain_id}'")
            if expr.scope.concept_class_id:
                conditions.append(f"concept_class_id = '{expr.scope.concept_class_id}'")
            if expr.scope.standard_concept != "any":
                conditions.append(f"standard_concept = '{expr.scope.standard_concept}'")
        conditions.append("invalid_reason IS NULL")
        where = " AND ".join(conditions)
        return f"SELECT concept_id FROM {SCHEMA_PLACEHOLDER}.CONCEPT WHERE {where}"

    def _compile_set_operation(self, expr: SetOperationNode) -> str:
        if len(expr.operands) < 2:
            raise ValueError("SetOperationNode requires at least 2 operands")
        subqueries = [f"({self.compile_expression(op)})" for op in expr.operands]
        sql_op = self._sql_operator(expr.operation)
        separator = f"\n  {sql_op}\n"
        return separator.join(subqueries)

    @staticmethod
    def _sql_operator(op: SetOperation) -> str:
        mapping = {
            SetOperation.UNION: "UNION",
            SetOperation.INTERSECT: "INTERSECT",
            SetOperation.MINUS: "EXCEPT",
        }
        return mapping[op]
