"""
Episode SQL Builder

This module contains the SQL builder for Episode criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..criteria import Episode
from .base import CriteriaSqlBuilder
from .utils import BuilderOptions, BuilderUtils, CriteriaColumn


class EpisodeSqlBuilder(CriteriaSqlBuilder[Episode]):
    """SQL builder for Episode criteria.

    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.EpisodeSqlBuilder
    """

    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.DOMAIN_CONCEPT,
    }

    DEFAULT_SELECT_COLUMNS = [
        "ep.person_id",
        "ep.episode_id",
        "ep.episode_concept_id",
        "ep.episode_number",
        "ep.episode_object_concept_id",
        "ep.episode_type_concept_id",
    ]

    def get_query_template(self) -> str:
        """Get the SQL query template for episode criteria."""
        return """-- Begin Episode Criteria
select C.person_id, C.episode_id as event_id, C.start_date, C.end_date,
  CAST(NULL as bigint) as visit_occurrence_id, C.start_date as sort_date@additionalColumns
from 
(
  select @selectClause @ordinalExpression
  FROM @cdm_database_schema.EPISODE ep
  @codesetClause
) C
@joinClause
@whereClause
-- End Episode Criteria
"""

    def get_default_columns(self) -> set[CriteriaColumn]:
        """Get default columns for episode criteria."""
        return self.DEFAULT_COLUMNS

    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DOMAIN_CONCEPT: "C.episode_concept_id",
            CriteriaColumn.DURATION: "DATEDIFF(d, C.start_date, C.end_date)",
        }
        return column_mapping.get(criteria_column, "NULL")

    def embed_codeset_clause(self, query: str, criteria: Episode) -> str:
        """Embed codeset clause in query."""
        codeset_clause = BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id,
            "ep.episode_concept_id",
            None,
            None,
        )
        return query.replace("@codesetClause", codeset_clause)

    def embed_ordinal_expression(self, query: str, criteria: Episode, where_clauses: list[str]) -> str:
        """Embed ordinal expression in query."""
        if criteria.first is not None and criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace(
                "@ordinalExpression",
                ", row_number() over (PARTITION BY ep.person_id ORDER BY ep.episode_start_date, ep.episode_id) as ordinal",
            )
        else:
            query = query.replace("@ordinalExpression", "")
        return query

    def resolve_select_clauses(
        self,
        criteria: Episode,
        options: BuilderOptions | None = None,
    ) -> list[str]:
        """Resolve select clauses for episode criteria."""
        select_cols = list(self.DEFAULT_SELECT_COLUMNS)

        if criteria.date_adjustment is not None:
            start_column = (
                "ep.episode_start_date"
                if criteria.date_adjustment.start_with == "start_date"
                else "ep.episode_end_date"
            )
            end_column = (
                "ep.episode_start_date"
                if criteria.date_adjustment.end_with == "start_date"
                else "ep.episode_end_date"
            )
            select_cols.append(
                BuilderUtils.get_date_adjustment_expression(
                    criteria.date_adjustment, start_column, end_column
                )
            )
        else:
            select_cols.append("ep.episode_start_date as start_date, ep.episode_end_date as end_date")

        return select_cols

    def resolve_join_clauses(self, criteria: Episode, options: BuilderOptions | None = None) -> list[str]:
        """Resolve join clauses for episode criteria."""
        join_clauses = []

        if criteria.age is not None or criteria.gender_cs is not None:
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")

        return join_clauses

    def resolve_where_clauses(self, criteria: Episode, options: BuilderOptions | None = None) -> list[str]:
        """Resolve where clauses for episode criteria."""
        where_clauses = []

        if criteria.episode_start_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.start_date", criteria.episode_start_date)
            if date_clause:
                where_clauses.append(date_clause)

        if criteria.episode_end_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.end_date", criteria.episode_end_date)
            if date_clause:
                where_clauses.append(date_clause)

        if criteria.episode_number is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause(
                "C.episode_number", criteria.episode_number
            )
            if numeric_clause:
                where_clauses.append(numeric_clause)

        if criteria.age is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause(
                "YEAR(C.start_date) - P.year_of_birth", criteria.age
            )
            if numeric_clause:
                where_clauses.append(numeric_clause)

        if criteria.gender_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(
                criteria.gender_cs.codeset_id,
                "P.gender_concept_id",
                criteria.gender_cs.is_exclusion,
            )
            if codeset_clause:
                where_clauses.append(codeset_clause)

        if criteria.episode_object_concept_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(
                criteria.episode_object_concept_cs.codeset_id,
                "C.episode_object_concept_id",
                criteria.episode_object_concept_cs.is_exclusion,
            )
            if codeset_clause:
                where_clauses.append(codeset_clause)

        if criteria.episode_type_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(
                criteria.episode_type_cs.codeset_id,
                "C.episode_type_concept_id",
                criteria.episode_type_cs.is_exclusion,
            )
            if codeset_clause:
                where_clauses.append(codeset_clause)

        return where_clauses
