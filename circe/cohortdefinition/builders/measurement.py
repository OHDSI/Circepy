"""
Measurement SQL Builder

This module contains the SQL builder for Measurement criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import Measurement


class MeasurementSqlBuilder(CriteriaSqlBuilder[Measurement]):
    """SQL builder for Measurement criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.MeasurementSqlBuilder
    """
    
    def get_query_template(self) -> str:
        """Get the SQL query template for measurement criteria."""
        return """-- Begin Measurement Criteria
select C.person_id, C.measurement_id as event_id, C.start_date, C.end_date,
       C.visit_occurrence_id, C.start_date as sort_date@additionalColumns
from 
(
  select @selectClause @ordinalExpression
  FROM @cdm_database_schema.MEASUREMENT m
@codesetClause
) C
@joinClause
@whereClause
-- End Measurement Criteria
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for measurement criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.VISIT_ID
        }
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.START_DATE: "C.measurement_date",
            CriteriaColumn.END_DATE: "C.measurement_date",
            CriteriaColumn.DOMAIN_CONCEPT: "C.measurement_concept_id",
            CriteriaColumn.DURATION: "NULL",
            CriteriaColumn.VISIT_ID: "C.visit_occurrence_id",
            CriteriaColumn.AGE: "C.value_as_number"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    def embed_codeset_clause(self, query: str, criteria: Measurement) -> str:
        """Embed codeset clause for measurement criteria."""
        if criteria.codeset_id is None:
            return query.replace("@codesetClause", "")
        
        # Use JOIN syntax for codeset, not WHERE clause
        codeset_clause = f"JOIN #Codesets cs on (m.measurement_concept_id = cs.concept_id and cs.codeset_id = {criteria.codeset_id})"
        return query.replace("@codesetClause", codeset_clause)
    
    def resolve_select_clauses(self, criteria: Measurement, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for measurement criteria.
        
        Java equivalent: MeasurementSqlBuilder.resolveSelectClauses()
        """
        # Default select columns that are always returned from inner subquery
        select_cols = [
            "m.person_id",
            "m.measurement_id", 
            "m.measurement_concept_id",
            "m.visit_occurrence_id"
        ]
        
        # Add value columns if they might be used for filtering
        select_cols.append("m.value_as_number")
        select_cols.append("m.range_high")
        select_cols.append("m.range_low")
        select_cols.append("m.unit_concept_id")
        
        # Add date columns (start_date and end_date) with proper calculation for end_date
        select_cols.append("m.measurement_date as start_date")
        select_cols.append(" DATEADD(day,1,m.measurement_date) as end_date")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: Measurement, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for measurement criteria.
        
        Java equivalent: MeasurementSqlBuilder.resolveJoinClauses()
        """
        join_clauses = []
        
        # Join to PERSON if age or gender conditions are present
        if criteria.age or (criteria.gender_cs and criteria.gender_cs.codeset_id):
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        # Join to PROVIDER if provider specialty conditions are present
        # Use "PR" alias to avoid conflict with PERSON alias
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            join_clauses.append("JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id")
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: Measurement, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for measurement criteria.
        
        Java equivalent: MeasurementSqlBuilder.resolveWhereClauses()
        """
        where_clauses = []
        
        # Note: codeset filtering is now handled via JOIN in inner query, not WHERE clause
        
        # Add occurrence start date condition
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_start_date, "C.start_date"
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        # Add occurrence end date condition
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
        
        # Add value as number condition
        if criteria.value_as_number:
            value_clause = BuilderUtils.build_numeric_range_clause(
                criteria.value_as_number, "C.value_as_number"
            )
            if value_clause:
                where_clauses.append(value_clause)
        
        # Add unit condition using unit concept list or concept set
        if criteria.unit:
            # Extract concept IDs from unit list
            unit_ids = [str(concept.concept_id) for concept in criteria.unit if hasattr(concept, 'concept_id')]
            if unit_ids:
                where_clauses.append(f"C.unit_concept_id in ({','.join(unit_ids)})")
        
        if criteria.unit_cs and criteria.unit_cs.codeset_id:
            unit_clause = BuilderUtils.get_codeset_in_expression(
                criteria.unit_cs.codeset_id,
                "C.unit_concept_id",
                criteria.unit_cs.is_exclusion
            )
            if unit_clause:
                where_clauses.append(unit_clause)
        
        # Add value as string condition
        if criteria.value_as_string:
            value_clause = BuilderUtils.build_text_filter_clause(
                criteria.value_as_string, "C.value_as_string"
            )
            if value_clause:
                where_clauses.append(value_clause)
        
        # Add range conditions
        if criteria.range_low:
            range_clause = BuilderUtils.build_numeric_range_clause(
                criteria.range_low, "C.range_low"
            )
            if range_clause:
                where_clauses.append(range_clause)
        
        if criteria.range_high:
            range_clause = BuilderUtils.build_numeric_range_clause(
                criteria.range_high, "C.range_high"
            )
            if range_clause:
                where_clauses.append(range_clause)
        
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
        
        Java equivalent: MeasurementSqlBuilder.getAdditionalColumns()
        """
        return ", ".join([f"{self.get_table_column_for_criteria_column(col)} as {col.value}" for col in columns])
    
    def embed_ordinal_expression(self, query: str, criteria: Measurement, options: Optional[BuilderOptions] = None) -> str:
        """Embed ordinal expression for measurement criteria."""
        ordinal_expression = self.resolve_ordinal_expression(criteria, options)
        return query.replace("@ordinalExpression", ordinal_expression)
    
    def resolve_ordinal_expression(self, criteria: Measurement, options: Optional[BuilderOptions] = None) -> str:
        """Resolve ordinal expression for measurement criteria."""
        if criteria.first:
            return ", ROW_NUMBER() OVER (PARTITION BY m.person_id ORDER BY m.measurement_date, m.measurement_id) ordinal"
        return ""
