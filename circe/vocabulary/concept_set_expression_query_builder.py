"""
Concept Set Expression Query Builder

This module contains the SQL builder for concept set expressions.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import TYPE_CHECKING, Optional

from ..cohortdefinition.builders.utils import BuilderUtils
from .concept import Concept, ConceptExpressionItem, ConceptSetExpression

if TYPE_CHECKING:
    from .predicate_sql_compiler import PredicateSQLCompiler


class ConceptSetExpressionQueryBuilder:
    """SQL builder for concept set expressions.

    Java equivalent: org.ohdsi.circe.vocabulary.ConceptSetExpressionQueryBuilder
    """

    # SQL templates - equivalent to Java ResourceHelper.GetResourceAsString
    CONCEPT_SET_QUERY_TEMPLATE = (
        "select concept_id from @vocabulary_database_schema.CONCEPT where @conceptIdIn"
    )

    CONCEPT_SET_DESCENDANTS_TEMPLATE = """  select c.concept_id
  from @vocabulary_database_schema.CONCEPT c
  join @vocabulary_database_schema.CONCEPT_ANCESTOR ca on c.concept_id = ca.descendant_concept_id
  WHERE c.invalid_reason is null
  and @conceptIdIn"""

    CONCEPT_SET_MAPPED_TEMPLATE = """select distinct cr.concept_id_1 as concept_id
FROM
(
  @conceptsetQuery
) C
join @vocabulary_database_schema.concept_relationship cr on C.concept_id = cr.concept_id_2 and cr.relationship_id = 'Maps to' and cr.invalid_reason IS NULL"""

    CONCEPT_SET_INCLUDE_TEMPLATE = """select distinct I.concept_id FROM
( 
  @includeQuery
) I"""

    CONCEPT_SET_EXCLUDE_TEMPLATE = """LEFT JOIN
(
  @excludeQuery
) E ON I.concept_id = E.concept_id
WHERE E.concept_id is null"""

    MAX_IN_LENGTH = 1000  # Oracle limitation

    def get_concept_ids(self, concepts: list[Concept]) -> list[int]:
        """Get concept IDs from concept list.

        Java equivalent: getConceptIds()
        """
        return [concept.concept_id for concept in concepts if concept.concept_id is not None]

    def build_concept_set_sub_query(self, concepts: list[Concept], descendant_concepts: list[Concept]) -> str:
        """Build concept set sub-query.

        Java equivalent: buildConceptSetSubQuery()
        """
        queries = []

        if concepts:
            concept_ids = self.get_concept_ids(concepts)
            concept_id_in = BuilderUtils.split_in_clause("concept_id", concept_ids, self.MAX_IN_LENGTH)
            query = self.CONCEPT_SET_QUERY_TEMPLATE.replace("@conceptIdIn", concept_id_in)
            queries.append(query)

        if descendant_concepts:
            descendant_ids = self.get_concept_ids(descendant_concepts)
            concept_id_in = BuilderUtils.split_in_clause(
                "ca.ancestor_concept_id", descendant_ids, self.MAX_IN_LENGTH
            )
            query = self.CONCEPT_SET_DESCENDANTS_TEMPLATE.replace("@conceptIdIn", concept_id_in)
            queries.append(query)

        return " UNION ".join(queries)

    def build_concept_set_mapped_query(
        self,
        mapped_concepts: list[Concept],
        mapped_descendant_concepts: list[Concept],
    ) -> str:
        """Build concept set mapped query.

        Java equivalent: buildConceptSetMappedQuery()
        """
        concept_set_query = self.build_concept_set_sub_query(mapped_concepts, mapped_descendant_concepts)
        return self.CONCEPT_SET_MAPPED_TEMPLATE.replace("@conceptsetQuery", concept_set_query)

    def build_concept_set_query(
        self,
        concepts: list[Concept],
        descendant_concepts: list[Concept],
        mapped_concepts: list[Concept],
        mapped_descendant_concepts: list[Concept],
    ) -> str:
        """Build concept set query.

        Java equivalent: buildConceptSetQuery()
        """
        if not concepts:
            return "select concept_id from @vocabulary_database_schema.CONCEPT where 0=1"

        concept_set_query = self.build_concept_set_sub_query(concepts, descendant_concepts)

        if mapped_concepts or mapped_descendant_concepts:
            mapped_query = self.build_concept_set_mapped_query(mapped_concepts, mapped_descendant_concepts)
            concept_set_query += " UNION " + mapped_query

        return concept_set_query

    def build_expression_query(
        self,
        expression: ConceptSetExpression,
        predicate_compiler: Optional["PredicateSQLCompiler"] = None,
    ) -> str:
        """Build expression query for concept set.

        Supports both traditional ConceptExpressionItem and ConceptPredicateItem.
        Predicate items require a PredicateSQLCompiler to be provided.

        Java equivalent: buildExpressionQuery()
        """

        from .predicate_item import ConceptPredicateItem

        include_concepts = []
        include_descendant_concepts = []
        include_mapped_concepts = []
        include_mapped_descendant_concepts = []
        include_predicate_queries = []

        exclude_concepts = []
        exclude_descendant_concepts = []
        exclude_mapped_concepts = []
        exclude_mapped_descendant_concepts = []
        exclude_predicate_queries = []

        for item in expression.items:
            if isinstance(item, ConceptPredicateItem):
                if predicate_compiler is None:
                    raise ValueError("ConceptPredicateItem requires a PredicateSQLCompiler")
                sql = predicate_compiler.compile_expression(item.expression)
                if item.is_excluded:
                    exclude_predicate_queries.append(sql)
                else:
                    include_predicate_queries.append(sql)
            elif isinstance(item, ConceptExpressionItem):
                if not item.is_excluded:
                    include_concepts.append(item.concept)
                    if item.include_descendants:
                        include_descendant_concepts.append(item.concept)
                    if item.include_mapped:
                        include_mapped_concepts.append(item.concept)
                        if item.include_descendants:
                            include_mapped_descendant_concepts.append(item.concept)
                else:
                    exclude_concepts.append(item.concept)
                    if item.include_descendants:
                        exclude_descendant_concepts.append(item.concept)
                    if item.include_mapped:
                        exclude_mapped_concepts.append(item.concept)
                        if item.include_descendants:
                            exclude_mapped_descendant_concepts.append(item.concept)

        concept_set_query = self.build_concept_set_query(
            include_concepts,
            include_descendant_concepts,
            include_mapped_concepts,
            include_mapped_descendant_concepts,
        )

        if include_predicate_queries:
            predicate_union = " UNION ".join(include_predicate_queries)
            if concept_set_query != "select concept_id from @vocabulary_database_schema.CONCEPT where 0=1":
                concept_set_query += " UNION " + predicate_union
            else:
                concept_set_query = predicate_union

        concept_set_query = self.CONCEPT_SET_INCLUDE_TEMPLATE.replace("@includeQuery", concept_set_query)

        exclude_query_parts = []
        if exclude_concepts or include_mapped_concepts or include_mapped_descendant_concepts:
            eq = self.build_concept_set_query(
                exclude_concepts,
                exclude_descendant_concepts,
                exclude_mapped_concepts,
                exclude_mapped_descendant_concepts,
            )
            if eq != "select concept_id from @vocabulary_database_schema.CONCEPT where 0=1":
                exclude_query_parts.append(eq)
        if exclude_predicate_queries:
            exclude_query_parts.extend(exclude_predicate_queries)

        if exclude_query_parts:
            combined = " UNION ".join(exclude_query_parts)
            concept_set_query += self.CONCEPT_SET_EXCLUDE_TEMPLATE.replace("@excludeQuery", combined)

        return concept_set_query
