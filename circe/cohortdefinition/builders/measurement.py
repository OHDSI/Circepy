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
        return """
        SELECT 
            @selectClause
        FROM @cdm_database_schema.MEASUREMENT C
        @joinClause
        WHERE @whereClause
        @ordinalExpression
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
    
    def get_criteria_sql(self, criteria: Measurement, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for measurement criteria."""
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
    
    def embed_codeset_clause(self, query: str, criteria: Measurement) -> str:
        """Embed codeset clause for measurement criteria."""
        if criteria.codeset_id is None:
            return query.replace("@codesetClause", "")
        
        codeset_clause = BuilderUtils.get_codeset_in_expression(
            criteria.codeset_id, 
            "C.measurement_concept_id",
            criteria.measurement_type_exclude
        )
        return query.replace("@codesetClause", codeset_clause)
    
    def resolve_select_clauses(self, criteria: Measurement, options: BuilderOptions) -> List[str]:
        """Resolve select clauses for measurement criteria."""
        columns = list(self.get_default_columns())
        if options.additional_columns:
            columns.extend(options.additional_columns)
        
        select_parts = []
        for column in columns:
            table_column = self.get_table_column_for_criteria_column(column)
            select_parts.append(f"{table_column} as {column.value}")
        
        return select_parts
    
    def resolve_join_clauses(self, criteria: Measurement, options: BuilderOptions) -> List[str]:
        """Resolve join clauses for measurement criteria."""
        joins = []
        
        # Add provider specialty join if needed
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            joins.append(f"""
            JOIN @cdm_database_schema.PROVIDER P ON C.provider_id = P.provider_id
            """)
        
        return joins
    
    def resolve_where_clauses(self, criteria: Measurement, options: BuilderOptions) -> List[str]:
        """Resolve where clauses for measurement criteria."""
        conditions = []
        
        # Add codeset condition
        if criteria.codeset_id is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(
                criteria.codeset_id, 
                "C.measurement_concept_id",
                criteria.measurement_type_exclude
            )
            conditions.append(codeset_clause)
        
        # Add date range conditions
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_start_date, "C.measurement_date"
            )
            if date_clause:
                conditions.append(date_clause)
        
        if criteria.occurrence_end_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_end_date, "C.measurement_date"
            )
            if date_clause:
                conditions.append(date_clause)
        
        # Add age condition
        if criteria.age:
            age_clause = BuilderUtils.build_numeric_range_clause(
                criteria.age, "C.person_id"  # Would need age calculation
            )
            if age_clause:
                conditions.append(age_clause)
        
        # Add value as number condition
        if criteria.value_as_number:
            value_clause = BuilderUtils.build_numeric_range_clause(
                criteria.value_as_number, "C.value_as_number"
            )
            if value_clause:
                conditions.append(value_clause)
        
        # Add value as string condition
        if criteria.value_as_string:
            value_clause = BuilderUtils.build_text_filter_clause(
                criteria.value_as_string, "C.value_as_string"
            )
            if value_clause:
                conditions.append(value_clause)
        
        # Add range conditions
        if criteria.range_low:
            range_clause = BuilderUtils.build_numeric_range_clause(
                criteria.range_low, "C.range_low"
            )
            if range_clause:
                conditions.append(range_clause)
        
        if criteria.range_high:
            range_clause = BuilderUtils.build_numeric_range_clause(
                criteria.range_high, "C.range_high"
            )
            if range_clause:
                conditions.append(range_clause)
        
        # Add provider specialty condition
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            provider_clause = BuilderUtils.get_codeset_in_expression(
                criteria.provider_specialty_cs.codeset_id,
                "P.specialty_concept_id",
                criteria.provider_specialty_cs.is_exclusion
            )
            if provider_clause:
                conditions.append(provider_clause)
        
        return conditions if conditions else ["1=1"]
    
    def resolve_ordinal_expression(self, criteria: Measurement, options: BuilderOptions) -> str:
        """Resolve ordinal expression for measurement criteria."""
        if criteria.first:
            return "ORDER BY C.measurement_date ASC"
        return ""
