"""
Custom Era SQL Builder

This module contains the SQL builder for Custom Era criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..criteria import CustomEra
from .base import CriteriaSqlBuilder
from .utils import BuilderOptions, BuilderUtils, CriteriaColumn


class CustomEraSqlBuilder(CriteriaSqlBuilder[CustomEra]):
    """SQL builder for Custom Era criteria.

    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.CustomEraSqlBuilder
    """

    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.VISIT_ID,
    }

    def get_query_template(self) -> str:
        """Get the SQL query template for custom era criteria."""
        return """select C.person_id, C.event_id, C.start_date, C.end_date,
  CAST(NULL as bigint) as visit_occurrence_id, C.start_date as sort_date@additionalColumns
from 
(
  select @selectClause @ordinalExpression
  from 
  (
    select person_id, min(start_date) as start_date, DATEADD(day,-1 * @eraconstructorpad, max(end_date)) as end_date
    from (
      select person_id, start_date, end_date, sum(is_start) over (partition by person_id order by start_date, is_start desc rows unbounded preceding) group_idx
      from (
        select person_id, start_date, DATEADD(day,@eraconstructorpad,end_date) as end_date,
          case when max(end_date) over (partition by person_id order by start_date rows between unbounded preceding and 1 preceding) >= start_date then 0 else 1 end is_start
        from (
          @criteriaQueries
        ) D
      ) CR
    ) ST
    group by person_id, group_idx
  ) E
) C
@joinClause
@whereClause
"""

    def get_default_columns(self) -> set[CriteriaColumn]:
        """Get default columns for custom era criteria."""
        return self.DEFAULT_COLUMNS

    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DURATION: "DATEDIFF(d, C.start_date, C.end_date)",
        }
        return column_mapping.get(criteria_column, "NULL")

    def embed_codeset_clause(self, query: str, criteria: CustomEra) -> str:
        """Embed codeset clause in query.

        Custom era criteria do not have their own codeset clause.
        """
        return query

    def embed_ordinal_expression(self, query: str, criteria: CustomEra, where_clauses: list[str]) -> str:
        """Embed ordinal expression in query."""
        if criteria.first is not None and criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace(
                "@ordinalExpression",
                ", row_number() over (PARTITION BY E.person_id ORDER BY E.start_date, E.end_date) as ordinal",
            )
        else:
            query = query.replace("@ordinalExpression", "")
        return query

    def resolve_select_clauses(
        self,
        criteria: CustomEra,
        options: BuilderOptions | None = None,
    ) -> list[str]:
        """Resolve select clauses for custom era criteria."""
        select_cols = [
            "E.person_id",
            "row_number() over (ORDER BY E.person_id, E.start_date, E.end_date) as event_id",
        ]

        if criteria.date_adjustment is not None:
            adjustment = criteria.date_adjustment
            start_column = "E.start_date" if adjustment.start_with == "start_date" else "E.end_date"
            end_column = "E.start_date" if adjustment.end_with == "start_date" else "E.end_date"
            select_cols.append(
                BuilderUtils.get_date_adjustment_expression(
                    criteria.date_adjustment, start_column, end_column
                )
            )
        else:
            select_cols.append("E.start_date as start_date, E.end_date as end_date")

        return select_cols

    def resolve_join_clauses(self, criteria: CustomEra, options: BuilderOptions | None = None) -> list[str]:
        """Resolve join clauses for custom era criteria."""
        join_clauses = []

        if criteria.age_at_start is not None or criteria.gender_cs is not None:
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")

        return join_clauses

    def resolve_where_clauses(self, criteria: CustomEra, options: BuilderOptions | None = None) -> list[str]:
        """Resolve where clauses for custom era criteria."""
        where_clauses = []

        if criteria.start_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.start_date", criteria.start_date)
            if date_clause:
                where_clauses.append(date_clause)

        if criteria.end_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.end_date", criteria.end_date)
            if date_clause:
                where_clauses.append(date_clause)

        if criteria.age_at_start is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause(
                "YEAR(C.start_date) - P.year_of_birth", criteria.age_at_start
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

        if criteria.duration is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause(
                "DATEDIFF(d,C.start_date, C.end_date)", criteria.duration
            )
            if numeric_clause:
                where_clauses.append(numeric_clause)

        return where_clauses

    def get_criteria_sql_with_options(
        self,
        criteria: CustomEra,
        options: BuilderOptions | None,
        criteria_query: str | None = None,
    ) -> str:
        """Get SQL query for custom era criteria with the nested criteria query.

        Java equivalent: CustomEraSqlBuilder.getCriteriaSql(T criteria, BuilderOptions options, String criteriaQuery)
        """
        query = super().get_criteria_sql_with_options(criteria, options)
        query = query.replace(
            "@eraconstructorpad", str(criteria.gap_days if criteria.gap_days is not None else 0)
        )
        if criteria_query is not None:
            query = query.replace("@criteriaQueries", criteria_query)
        return query
