"""
Observation SQL Builder

This module contains the SQL builder for Observation criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import Observation


class ObservationSqlBuilder(CriteriaSqlBuilder[Observation]):
    """SQL builder for Observation criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.ObservationSqlBuilder
    """
    
    def get_query_template(self) -> str:
        """Get the SQL query template for observation criteria."""
        return """-- Begin Observation Criteria
select C.person_id, C.observation_id as event_id, C.start_date, C.END_DATE,
       C.visit_occurrence_id, C.start_date as sort_date@additionalColumns
from 
(
  select @selectClause @ordinalExpression
  FROM @cdm_database_schema.OBSERVATION o
@codesetClause
) C
@joinClause
@whereClause
-- End Observation Criteria
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for observation criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.VISIT_ID
        }
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.START_DATE: "C.observation_date",
            CriteriaColumn.END_DATE: "C.observation_date",
            CriteriaColumn.DOMAIN_CONCEPT: "C.observation_concept_id",
            CriteriaColumn.DURATION: "NULL",
            CriteriaColumn.VISIT_ID: "C.visit_occurrence_id",
            CriteriaColumn.AGE: "C.value_as_string"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    
    def embed_codeset_clause(self, query: str, criteria: Observation) -> str:
        """Embed codeset clause for observation criteria."""
        if criteria.codeset_id is None:
            return query.replace("@codesetClause", "")
        
        # Use JOIN syntax for codeset, not WHERE clause
        codeset_clause = f"JOIN #Codesets cs on (o.observation_concept_id = cs.concept_id and cs.codeset_id = {criteria.codeset_id})"
        return query.replace("@codesetClause", codeset_clause)
    
    def resolve_select_clauses(self, criteria: Observation, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for observation criteria.
        
        Java equivalent: ObservationSqlBuilder.resolveSelectClauses()
        """
        # Default select columns that are always returned from inner subquery
        select_cols = [
            "o.person_id",
            "o.observation_id", 
            "o.observation_concept_id",
            "o.visit_occurrence_id",
            "o.value_as_number"  # Always include for compatibility with reference SQL
        ]
        
        # Add date columns (start_date and end_date)
        select_cols.append("o.observation_date as start_date")
        select_cols.append("DATEADD(day,1,o.observation_date) as end_date")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: Observation, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for observation criteria.
        
        Java equivalent: ObservationSqlBuilder.resolveJoinClauses()
        """
        join_clauses = []
        
        # Join to PERSON if age or gender conditions are present
        if criteria.age or (criteria.gender_cs and criteria.gender_cs.codeset_id):
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        # Join to PROVIDER if provider specialty conditions are present
        # Always use PR alias for PROVIDER to match Java implementation
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            join_clauses.append("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id")
        
        # Join to VISIT_OCCURRENCE if visit type conditions are present
        if criteria.visit_type_cs and criteria.visit_type_cs.codeset_id:
            join_clauses.append("JOIN @cdm_database_schema.VISIT_OCCURRENCE VO on C.visit_occurrence_id = VO.visit_occurrence_id")
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: Observation, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for observation criteria."""
        where_clauses = []
        
        # Add date range conditions
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_start_date, "C.start_date"
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        if criteria.occurrence_end_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_end_date, "C.end_date"
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        # Add age condition
        if criteria.age:
            age_clause = BuilderUtils.build_numeric_range_clause(
                criteria.age, "YEAR(C.start_date) - P.year_of_birth"
            )
            if age_clause:
                where_clauses.append(age_clause)
        
        # Add value as string condition
        if criteria.value_as_string:
            value_clause = BuilderUtils.build_text_filter_clause(
                criteria.value_as_string, "C.value_as_string"
            )
            if value_clause:
                where_clauses.append(value_clause)
        
        # Add provider specialty condition
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            provider_clause = BuilderUtils.get_codeset_in_expression(
                criteria.provider_specialty_cs.codeset_id,
                "PR.specialty_concept_id",
                criteria.provider_specialty_cs.is_exclusion
            )
            if provider_clause:
                where_clauses.append(provider_clause)
        
        return where_clauses
    
    def get_additional_columns(self, columns: List[CriteriaColumn]) -> str:
        """Get additional columns string with proper aliases.
        
        Java equivalent: ObservationSqlBuilder.getAdditionalColumns()
        """
        return ", ".join([f"{self.get_table_column_for_criteria_column(col)} as {col.value}" for col in columns])
    
    def embed_ordinal_expression(self, query: str, criteria: Observation, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query."""
        # first
        if criteria.first is not None and criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace("@ordinalExpression", ", row_number() over (PARTITION BY o.person_id ORDER BY o.observation_date, o.observation_id) as ordinal")
        else:
            query = query.replace("@ordinalExpression", "")
        return query
    
    def resolve_ordinal_expression(self, criteria: Observation, options: BuilderOptions) -> str:
        """Resolve ordinal expression for observation criteria."""
        if criteria.first:
            return ", row_number() over (PARTITION BY o.person_id ORDER BY o.observation_date, o.observation_id) as ordinal"
        return ""
