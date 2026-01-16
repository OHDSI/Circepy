"""
Payer Plan Period SQL Builder

This module contains the SQL builder for Payer Plan Period criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import PayerPlanPeriod


class PayerPlanPeriodSqlBuilder(CriteriaSqlBuilder[PayerPlanPeriod]):
    """SQL builder for Payer Plan Period criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.PayerPlanPeriodSqlBuilder
    """
    
    # Default columns are those that are specified in the template, and don't need to be added if specified in 'additionalColumns'
    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.VISIT_ID
    }
    
    # Default select columns are the columns that will always be returned from the subquery, but are added to based on the specific criteria
    DEFAULT_SELECT_COLUMNS = [
        "ppp.person_id",
        "ppp.payer_plan_period_id"
    ]
    
    def get_query_template(self) -> str:
        """Get the SQL query template for payer plan period criteria."""
        return """
        SELECT 
            @selectClause@additionalColumns
        FROM (
            SELECT 
                ppp.person_id,
                ppp.payer_plan_period_id,
                ppp.payer_concept_id,
                ppp.plan_concept_id,
                ppp.sponsor_concept_id,
                ppp.stop_reason_concept_id,
                ppp.payer_source_concept_id,
                ppp.plan_source_concept_id,
                ppp.sponsor_source_concept_id,
                ppp.stop_reason_source_concept_id,
                ppp.payer_plan_period_start_date,
                ppp.payer_plan_period_end_date
                @ordinalExpression
            FROM @cdm_database_schema.PAYER_PLAN_PERIOD ppp
            @codesetClause
        ) C
        @joinClause
        WHERE @whereClause
        @additionalColumns
        """
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for payer plan period criteria."""
        return self.DEFAULT_COLUMNS
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DOMAIN_CONCEPT: "C.payer_concept_id",
            CriteriaColumn.START_DATE: "C.start_date",
            CriteriaColumn.END_DATE: "C.end_date",
            CriteriaColumn.VISIT_ID: "NULL",
            CriteriaColumn.VISIT_ID: "NULL"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    def get_criteria_sql_with_options(self, criteria: PayerPlanPeriod, options: Optional[BuilderOptions]) -> str:
        """Get SQL query for criteria with builder options."""
        query = super().get_criteria_sql_with_options(criteria, options)
        
        start_date_expression = (BuilderUtils.date_string_to_sql(criteria.user_defined_period.start_date) 
                                if criteria.user_defined_period is not None and criteria.user_defined_period.start_date is not None 
                                else "C.start_date")
        query = query.replace("@startDateExpression", start_date_expression)
        
        end_date_expression = (BuilderUtils.date_string_to_sql(criteria.user_defined_period.end_date) 
                              if criteria.user_defined_period is not None and criteria.user_defined_period.end_date is not None 
                              else "C.end_date")
        query = query.replace("@endDateExpression", end_date_expression)
        
        return query
    
    def embed_codeset_clause(self, query: str, criteria: PayerPlanPeriod) -> str:
        """Embed codeset clause in query."""
        return query.replace("@codesetClause", "")
    
    def embed_ordinal_expression(self, query: str, criteria: PayerPlanPeriod, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query."""
        return query.replace("@ordinalExpression", "")
    
    def resolve_select_clauses(self, criteria: PayerPlanPeriod, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for payer plan period criteria."""
        select_cols = list(self.DEFAULT_SELECT_COLUMNS)
        
        # payer concept
        if criteria.payer_concept is not None:
            select_cols.append("ppp.payer_concept_id")
        
        # plan concept
        if criteria.plan_concept is not None:
            select_cols.append("ppp.plan_concept_id")
        
        # sponsor concept
        if criteria.sponsor_concept is not None:
            select_cols.append("ppp.sponsor_concept_id")
        
        # stop reason concept
        if criteria.stop_reason_concept is not None:
            select_cols.append("ppp.stop_reason_concept_id")
        
        # payer SourceConcept
        if criteria.payer_source_concept is not None:
            select_cols.append("ppp.payer_source_concept_id")
        
        # plan SourceConcept
        if criteria.plan_source_concept is not None:
            select_cols.append("ppp.plan_source_concept_id")
        
        # sponsor SourceConcept
        if criteria.sponsor_source_concept is not None:
            select_cols.append("ppp.sponsor_source_concept_id")
        
        # stop reason SourceConcept
        if criteria.stop_reason_source_concept is not None:
            select_cols.append("ppp.stop_reason_source_concept_id")
        
        # dateAdjustment or default start/end dates
        if criteria.date_adjustment is not None:
            start_column = "ppp.payer_plan_period_start_date" if criteria.date_adjustment.start_with == "start_date" else "ppp.payer_plan_period_end_date"
            end_column = "ppp.payer_plan_period_start_date" if criteria.date_adjustment.end_with == "start_date" else "ppp.payer_plan_period_end_date"
            select_cols.append(BuilderUtils.get_date_adjustment_expression(criteria.date_adjustment, start_column, end_column))
        else:
            select_cols.append("ppp.payer_plan_period_start_date as start_date")
            select_cols.append("ppp.payer_plan_period_end_date as end_date")
        
        # Add domain concept column
        select_cols.append("ppp.payer_concept_id as domain_concept")
        
        # Add visit_id column (payer plan period doesn't have visit_id, so use NULL)
        select_cols.append("NULL as visit_id")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: PayerPlanPeriod, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for payer plan period criteria."""
        join_clauses = []
        
        if (criteria.age_at_start is not None or 
            criteria.age_at_end is not None or 
            (criteria.gender is not None and len(criteria.gender) > 0) or
            criteria.gender_cs is not None):
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: PayerPlanPeriod, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for payer plan period criteria."""
        where_clauses = []
        
        # first
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
        
        # gender
        if criteria.gender is not None and hasattr(criteria.gender, '__len__') and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            if concept_ids:
                where_clauses.append(f"P.gender_concept_id in ({','.join(map(str, concept_ids))})")
        
        # genderCS
        if criteria.gender_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(criteria.gender_cs.codeset_id, "P.gender_concept_id", criteria.gender_cs.is_exclusion)
            if codeset_clause:
                where_clauses.append(codeset_clause)
        
        # payer concept
        if criteria.payer_concept is not None:
            where_clauses.append(f"C.payer_concept_id in (SELECT concept_id from #Codesets where codeset_id = {criteria.payer_concept})")
        
        # plan concept
        if criteria.plan_concept is not None:
            where_clauses.append(f"C.plan_concept_id in (SELECT concept_id from #Codesets where codeset_id = {criteria.plan_concept})")
        
        # sponsor concept
        if criteria.sponsor_concept is not None:
            where_clauses.append(f"C.sponsor_concept_id in (SELECT concept_id from #Codesets where codeset_id = {criteria.sponsor_concept})")
        
        # stop reason concept
        if criteria.stop_reason_concept is not None:
            where_clauses.append(f"C.stop_reason_concept_id in (SELECT concept_id from #Codesets where codeset_id = {criteria.stop_reason_concept})")
        
        # payer SourceConcept
        if criteria.payer_source_concept is not None:
            where_clauses.append(f"C.payer_source_concept_id in (SELECT concept_id from #Codesets where codeset_id = {criteria.payer_source_concept})")
        
        # plan SourceConcept
        if criteria.plan_source_concept is not None:
            where_clauses.append(f"C.plan_source_concept_id in (SELECT concept_id from #Codesets where codeset_id = {criteria.plan_source_concept})")
        
        # sponsor SourceConcept
        if criteria.sponsor_source_concept is not None:
            where_clauses.append(f"C.sponsor_source_concept_id in (SELECT concept_id from #Codesets where codeset_id = {criteria.sponsor_source_concept})")
        
        # stop reason SourceConcept
        if criteria.stop_reason_source_concept is not None:
            where_clauses.append(f"C.stop_reason_source_concept_id in (SELECT concept_id from #Codesets where codeset_id = {criteria.stop_reason_source_concept})")
        
        return where_clauses if where_clauses else ["1=1"]
    
    def get_additional_columns(self, columns: List[CriteriaColumn]) -> str:
        """Get additional columns string with proper aliases.
        
        Java equivalent: PayerPlanPeriodSqlBuilder.getAdditionalColumns()
        """
        return ", ".join([f"{self.get_table_column_for_criteria_column(col)} as {col.value}" for col in columns])
