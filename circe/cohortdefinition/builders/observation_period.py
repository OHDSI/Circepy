"""
Observation Period SQL Builder

This module contains the SQL builder for Observation Period criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import ObservationPeriod


class ObservationPeriodSqlBuilder(CriteriaSqlBuilder[ObservationPeriod]):
    """SQL builder for Observation Period criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.ObservationPeriodSqlBuilder
    """
    
    # Default columns are those that are specified in the template, and don't need to be added if specified in 'additionalColumns'
    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.VISIT_ID
    }
    
    # Default select columns are the columns that will always be returned from the subquery, but are added to based on the specific criteria
    DEFAULT_SELECT_COLUMNS = [
        "op.person_id",
        "op.observation_period_id",
        "op.period_type_concept_id"
    ]
    
    def get_query_template(self) -> str:
        """Get the SQL query template for observation period criteria.
        
        This template matches the Java ObservationPeriodSqlBuilder template exactly.
        """
        return """-- Begin Observation Period Criteria
select C.person_id, C.observation_period_id as event_id, @startDateExpression as start_date, @endDateExpression as end_date,
       CAST(NULL as bigint) as visit_occurrence_id, C.start_date as sort_date@additionalColumns

from 
(
  select @selectClause , row_number() over (PARTITION BY op.person_id ORDER BY op.observation_period_start_date) as ordinal
  FROM @cdm_database_schema.OBSERVATION_PERIOD op
) C
@joinClause
@whereClause
-- End Observation Period Criteria
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for observation period criteria."""
        return self.DEFAULT_COLUMNS
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DOMAIN_CONCEPT: "C.period_type_concept_id",
            CriteriaColumn.DURATION: "DATEDIFF(d, @startDateExpression, @endDateExpression)",
            CriteriaColumn.START_DATE: "C.start_date",
            CriteriaColumn.END_DATE: "C.end_date",
            CriteriaColumn.VISIT_ID: "NULL",
            CriteriaColumn.VISIT_ID: "NULL"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    def get_criteria_sql_with_options(self, criteria: ObservationPeriod, options: Optional[BuilderOptions]) -> str:
        """Get SQL query for criteria with builder options."""
        query = super().get_criteria_sql_with_options(criteria, options)
        
        # Override user defined dates in select
        start_date_expression = (BuilderUtils.date_string_to_sql(criteria.user_defined_period.start_date) 
                                if criteria.user_defined_period is not None and criteria.user_defined_period.start_date is not None 
                                else "C.start_date")
        query = query.replace("@startDateExpression", start_date_expression)
        
        end_date_expression = (BuilderUtils.date_string_to_sql(criteria.user_defined_period.end_date) 
                              if criteria.user_defined_period is not None and criteria.user_defined_period.end_date is not None 
                              else "C.end_date")
        query = query.replace("@endDateExpression", end_date_expression)
        
        return query
    
    def embed_codeset_clause(self, query: str, criteria: ObservationPeriod) -> str:
        """Embed codeset clause in query."""
        return query.replace("@codesetClause", "")
    
    def embed_ordinal_expression(self, query: str, criteria: ObservationPeriod, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query."""
        return query.replace("@ordinalExpression", "")
    
    def resolve_select_clauses(self, criteria: ObservationPeriod, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for observation period criteria.
        
        Note: The outer SELECT in the template handles event_id, start_date, end_date, visit_occurrence_id, sort_date.
        This method only provides columns for the inner subquery.
        """
        select_cols = list(self.DEFAULT_SELECT_COLUMNS)
        
        # dateAdjustment or default start/end dates
        if criteria.date_adjustment is not None:
            start_column = "op.observation_period_start_date" if criteria.date_adjustment.start_with == "start_date" else "op.observation_period_end_date"
            end_column = "op.observation_period_start_date" if criteria.date_adjustment.end_with == "start_date" else "op.observation_period_end_date"
            select_cols.append(BuilderUtils.get_date_adjustment_expression(criteria.date_adjustment, start_column, end_column))
        else:
            select_cols.append("op.observation_period_start_date as start_date, op.observation_period_end_date as end_date")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: ObservationPeriod, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for observation period criteria."""
        join_clauses = []
        
        # join to PERSON
        if criteria.age_at_start is not None or criteria.age_at_end is not None:
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: ObservationPeriod, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for observation period criteria."""
        where_clauses = []
        
        if criteria.first is not None and criteria.first:
            where_clauses.append("C.ordinal = 1")
        
        # check for user defined start/end dates
        if criteria.user_defined_period is not None:
            user_defined_period = criteria.user_defined_period
            
            if user_defined_period.start_date is not None:
                start_date_expression = BuilderUtils.date_string_to_sql(user_defined_period.start_date)
                where_clauses.append(f"C.start_date <= {start_date_expression} and C.end_date >= {start_date_expression}")
            
            if user_defined_period.end_date is not None:
                end_date_expression = BuilderUtils.date_string_to_sql(user_defined_period.end_date)
                where_clauses.append(f"C.start_date <= {end_date_expression} and C.end_date >= {end_date_expression}")
        
        # periodStartDate
        if criteria.period_start_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.start_date", criteria.period_start_date)
            if date_clause:
                where_clauses.append(date_clause)
        
        # periodEndDate
        if criteria.period_end_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.end_date", criteria.period_end_date)
            if date_clause:
                where_clauses.append(date_clause)
        
        # periodType
        if criteria.period_type is not None and hasattr(criteria.period_type, '__len__') and len(criteria.period_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.period_type)
            if concept_ids:
                where_clauses.append(f"C.period_type_concept_id in ({','.join(map(str, concept_ids))})")
        
        # periodTypeCS
        if criteria.period_type_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(criteria.period_type_cs.codeset_id, "C.period_type_concept_id", criteria.period_type_cs.is_exclusion)
            if codeset_clause:
                where_clauses.append(codeset_clause)
        
        # periodLength
        if criteria.period_length is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause("DATEDIFF(d,C.start_date, C.end_date)", criteria.period_length)
            if numeric_clause:
                where_clauses.append(numeric_clause)
        
        # ageAtStart
        if criteria.age_at_start is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause("YEAR(C.start_date) - P.year_of_birth", criteria.age_at_start)
            if numeric_clause:
                where_clauses.append(numeric_clause)
        
        # ageAtEnd
        if criteria.age_at_end is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause("YEAR(C.end_date) - P.year_of_birth", criteria.age_at_end)
            if numeric_clause:
                where_clauses.append(numeric_clause)
        
        return where_clauses
    
    def get_additional_columns(self, columns: List[CriteriaColumn]) -> str:
        """Get additional columns string with proper aliases.
        
        Java equivalent: ObservationPeriodSqlBuilder.getAdditionalColumns()
        """
        return ", ".join([f"{self.get_table_column_for_criteria_column(col)} as {col.value}" for col in columns])
