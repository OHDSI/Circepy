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
        return """
        SELECT 
            @selectClause@additionalColumns
        FROM @cdm_database_schema.OBSERVATION C
        @joinClause
        WHERE @whereClause
        @ordinalExpression
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
    
    def get_criteria_sql(self, criteria: Observation, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for observation criteria."""
        if options is None:
            options = BuilderOptions()
        
        # Build select clause
        select_clause = ", ".join(self.resolve_select_clauses(criteria, options))
        
        # Build join clause
        join_clause = " ".join(self.resolve_join_clauses(criteria, options))
        
        # Build where clause
        where_clause = " AND ".join(self.resolve_where_clauses(criteria, options)) if self.resolve_where_clauses(criteria, options) else "1=1"
        
        # Build ordinal expression
        ordinal_expression = self.resolve_ordinal_expression(criteria, options)
        
        # Replace placeholders in template
        sql = self.get_query_template()
        sql = sql.replace("@selectClause", select_clause)
        sql = sql.replace("@joinClause", join_clause)
        sql = sql.replace("@whereClause", where_clause)
        sql = sql.replace("@ordinalExpression", ordinal_expression)
        
        return sql
    
    def embed_codeset_clause(self, query: str, criteria: Observation) -> str:
        """Embed codeset clause for observation criteria."""
        if criteria.codeset_id is None:
            return query.replace("@codesetClause", "")
        
        codeset_clause = BuilderUtils.get_codeset_in_expression(
            criteria.codeset_id, 
            "C.observation_concept_id",
            not criteria.observation_type_exclude if hasattr(criteria, 'observation_type_exclude') else False
        )
        return query.replace("@codesetClause", codeset_clause)
    
    def resolve_select_clauses(self, criteria: Observation, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for observation criteria.
        
        Java equivalent: ObservationSqlBuilder.resolveSelectClauses()
        """
        # Default select columns that are always returned
        select_cols = [
            "C.person_id",
            "C.observation_id", 
            "C.observation_concept_id"
        ]
        
        # Add date columns (start_date and end_date)
        select_cols.append("C.observation_date as start_date")
        select_cols.append("C.observation_date as end_date")
        
        # Add domain concept column
        select_cols.append("C.observation_concept_id as domain_concept")
        
        # Add visit_id column
        select_cols.append("C.visit_occurrence_id as visit_id")
        
        # Add additional columns from options if provided
        if options and options.additional_columns:
            filtered_columns = [
                column for column in options.additional_columns 
                if column not in self.get_default_columns()
            ]
            for col in filtered_columns:
                select_cols.append(f"{self.get_table_column_for_criteria_column(col)} as {col.value}")
        
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
    
    def resolve_where_clauses(self, criteria: Observation, options: BuilderOptions) -> List[str]:
        """Resolve where clauses for observation criteria."""
        where_clauses = []
        
        # Add codeset condition
        if criteria.codeset_id is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(
                criteria.codeset_id, 
                "C.observation_concept_id",
                criteria.observation_type_exclude
            )
            where_clauses.append(codeset_clause)
        
        # Add date range conditions
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_start_date, "C.observation_date"
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        if criteria.occurrence_end_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_end_date, "C.observation_date"
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        # Add age condition
        if criteria.age:
            age_clause = BuilderUtils.build_numeric_range_clause(
                criteria.age, "YEAR(C.observation_date) - P.year_of_birth"
            )
            if age_clause:
                where_clauses.append(age_clause)
                # Add person_id check for join requirement
                where_clauses.append("C.person_id = P.person_id")
        
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
        
        return where_clauses if where_clauses else ["1=1"]
    
    def get_additional_columns(self, columns: List[CriteriaColumn]) -> str:
        """Get additional columns string with proper aliases.
        
        Java equivalent: ObservationSqlBuilder.getAdditionalColumns()
        """
        return ", ".join([f"{self.get_table_column_for_criteria_column(col)} as {col.value}" for col in columns])
    
    def resolve_ordinal_expression(self, criteria: Observation, options: BuilderOptions) -> str:
        """Resolve ordinal expression for observation criteria."""
        if criteria.first:
            return "ORDER BY C.observation_date ASC"
        return ""
