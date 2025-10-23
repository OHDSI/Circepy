"""
Specimen SQL Builder

This module contains the SQL builder for Specimen criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import Specimen


class SpecimenSqlBuilder(CriteriaSqlBuilder[Specimen]):
    """SQL builder for Specimen criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.SpecimenSqlBuilder
    """
    
    def get_query_template(self) -> str:
        """Get the SQL query template for specimen criteria."""
        return """
        SELECT 
            @selectClause
        FROM @cdm_database_schema.SPECIMEN C
        @joinClause
        WHERE @whereClause
        @ordinalExpression
        """
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for specimen criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT
        }
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.START_DATE: "C.specimen_date",
            CriteriaColumn.END_DATE: "C.specimen_date",
            CriteriaColumn.DOMAIN_CONCEPT: "C.specimen_concept_id",
            CriteriaColumn.DURATION: "NULL",
            CriteriaColumn.VISIT_ID: "NULL",
            CriteriaColumn.AGE: "C.quantity"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    def get_criteria_sql(self, criteria: Specimen, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for specimen criteria."""
        if options is None:
            options = BuilderOptions()
        
        # Build select clause
        select_clause = self.resolve_select_clauses(criteria, options)
        
        # Build join clause
        join_clause = self.resolve_join_clauses(criteria, options)
        
        # Build where clause
        where_clause = self.resolve_where_clauses(criteria, options)
        
        # Build ordinal expression
        ordinal_expression = self.resolve_ordinal_expression(criteria, options)
        
        # Replace placeholders in template
        sql = self.get_query_template()
        sql = sql.replace("@selectClause", select_clause)
        sql = sql.replace("@joinClause", join_clause)
        sql = sql.replace("@whereClause", where_clause)
        sql = sql.replace("@ordinalExpression", ordinal_expression)
        
        return sql
    
    def embed_codeset_clause(self, query: str, criteria: Specimen) -> str:
        """Embed codeset clause for specimen criteria."""
        if criteria.codeset_id is None:
            return query.replace("@codesetClause", "")
        
        codeset_clause = BuilderUtils.get_codeset_in_expression(
            criteria.codeset_id, 
            "C.specimen_concept_id",
            not criteria.specimen_type_exclude if hasattr(criteria, 'specimen_type_exclude') else False
        )
        return query.replace("@codesetClause", codeset_clause)
    
    def resolve_select_clauses(self, criteria: Specimen, options: BuilderOptions) -> str:
        """Resolve select clauses for specimen criteria."""
        columns = list(self.get_default_columns())
        if options.additional_columns:
            columns.extend(options.additional_columns)
        
        select_parts = []
        for column in columns:
            table_column = self.get_table_column_for_criteria_column(column)
            select_parts.append(f"{table_column} as {column.value}")
        
        return ", ".join(select_parts)
    
    def resolve_join_clauses(self, criteria: Specimen, options: BuilderOptions) -> str:
        """Resolve join clauses for specimen criteria."""
        joins = []
        
        # Specimen table typically doesn't need additional joins
        return " ".join(joins)
    
    def resolve_where_clauses(self, criteria: Specimen, options: BuilderOptions) -> str:
        """Resolve where clauses for specimen criteria."""
        conditions = []
        
        # Add codeset condition
        codeset_clause = self.embed_codeset_clause("", criteria)
        if codeset_clause:
            conditions.append(codeset_clause)
        
        # Add date range conditions
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_start_date, "C.specimen_date"
            )
            if date_clause:
                conditions.append(date_clause)
        
        if criteria.occurrence_end_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_end_date, "C.specimen_date"
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
        
        # Add quantity condition
        if criteria.quantity:
            quantity_clause = BuilderUtils.build_numeric_range_clause(
                criteria.quantity, "C.quantity"
            )
            if quantity_clause:
                conditions.append(quantity_clause)
        
        return " AND ".join(conditions) if conditions else "1=1"
    
    def resolve_ordinal_expression(self, criteria: Specimen, options: BuilderOptions) -> str:
        """Resolve ordinal expression for specimen criteria."""
        if criteria.first:
            return "ORDER BY C.specimen_date ASC"
        return ""
