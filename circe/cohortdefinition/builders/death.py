"""
Death SQL Builder

This module contains the SQL builder for Death criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import Death


class DeathSqlBuilder(CriteriaSqlBuilder[Death]):
    """SQL builder for Death criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.DeathSqlBuilder
    """
    
    def get_query_template(self) -> str:
        """Get the SQL query template for death criteria."""
        # FIX: Updated template to match the standard OHDSI "Event" shape.
        # - Added 'event_id', 'visit_occurrence_id', 'sort_date'
        # - Used C.start_date/C.end_date instead of raw columns
        # - Removed hardcoded 'WHERE' and '@ordinalExpression'
        return """-- Begin Death Criteria
SELECT C.person_id, C.person_id as event_id, C.start_date, C.end_date,
       CAST(NULL as bigint) as visit_occurrence_id,
       C.start_date as sort_date@additionalColumns
FROM 
(
  SELECT @selectClause
  FROM @cdm_database_schema.DEATH d
  @codesetClause
) C
@joinClause
@whereClause
-- End Death Criteria
"""

    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for death criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID
        }

    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DOMAIN_CONCEPT: "coalesce(C.cause_concept_id,0)",
            CriteriaColumn.DURATION: "CAST(1 as int)",
            CriteriaColumn.START_DATE: "C.start_date",
            CriteriaColumn.END_DATE: "C.end_date"
        }
        return column_mapping.get(criteria_column, "NULL")


    def embed_codeset_clause(self, query: str, criteria: Death) -> str:
        """Embed codeset clause for death criteria."""
        return query.replace("@codesetClause", BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id,
            "d.cause_concept_id",
            criteria.death_source_concept,
            "d.cause_source_concept_id"
        ))

    def embed_ordinal_expression(self, query: str, criteria: Death, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query.

        Java DeathSqlBuilder overrides this to return query as is.
        Note: The @ordinalExpression token was removed from get_query_template above
        to prevent 'Token not found' errors or leakage.
        """
        return query

    def resolve_select_clauses(self, criteria: Death, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for death criteria."""
        select_cols = [
            "d.person_id",
            "d.cause_concept_id"
        ]

        # deathType
        if (criteria.death_type and len(criteria.death_type) > 0) or \
           (criteria.death_type_cs and criteria.death_type_cs.codeset_id):
            select_cols.append("d.death_type_concept_id")

        # dateAdjustment or default start/end dates
        if criteria.date_adjustment:
             select_cols.append(BuilderUtils.get_date_adjustment_expression(
                criteria.date_adjustment, "d.death_date", "DATEADD(day,1,d.death_date)"
             ))
        else:
             # FIX: Added 'as start_date' to align with outer query expectation
             select_cols.append("d.death_date as start_date, DATEADD(day,1,d.death_date) as end_date")

        return select_cols

    def resolve_join_clauses(self, criteria: Death, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for death criteria."""
        joins = []

        # join to PERSON
        if criteria.age or \
           (criteria.gender and len(criteria.gender) > 0) or \
           (criteria.gender_cs and criteria.gender_cs.codeset_id):
            joins.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")

        return joins

    def resolve_where_clauses(self, criteria: Death, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for death criteria."""
        where_clauses = super().resolve_where_clauses(criteria)

        # occurrenceStartDate
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                "C.start_date", criteria.occurrence_start_date
            )
            if date_clause:
                where_clauses.append(date_clause)

        # deathType
        if criteria.death_type and len(criteria.death_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.death_type)
            op = "not in" if criteria.death_type_exclude else "in"
            where_clauses.append(f"C.death_type_concept_id {op} ({','.join(map(str, concept_ids))})")

        # deathTypeCS
        if criteria.death_type_cs and criteria.death_type_cs.codeset_id:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.death_type_cs.codeset_id, "C.death_type_concept_id"))

        # age
        if criteria.age:
            where_clauses.append(BuilderUtils.build_numeric_range_clause(
                "YEAR(C.start_date) - P.year_of_birth", criteria.age
            ))

        # gender
        if criteria.gender and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            where_clauses.append(f"P.gender_concept_id in ({','.join(map(str, concept_ids))})")

        # genderCS
        if criteria.gender_cs and criteria.gender_cs.codeset_id:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.gender_cs.codeset_id, "P.gender_concept_id"))

        return where_clauses