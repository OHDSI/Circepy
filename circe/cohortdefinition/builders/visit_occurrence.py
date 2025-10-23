"""
Visit Occurrence SQL Builder

This module contains the SQL builder for Visit Occurrence criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import VisitOccurrence


class VisitOccurrenceSqlBuilder(CriteriaSqlBuilder[VisitOccurrence]):
    """SQL builder for Visit Occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.VisitOccurrenceSqlBuilder
    """
    
    def get_query_template(self) -> str:
        """Get the SQL query template for visit occurrence criteria."""
        return """
        SELECT 
            @selectClause
        FROM @cdm_database_schema.VISIT_OCCURRENCE C
        @joinClause
        WHERE @whereClause
        @ordinalExpression
        """
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for visit occurrence criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.VISIT_ID
        }
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.START_DATE: "C.visit_start_date",
            CriteriaColumn.END_DATE: "C.visit_end_date",
            CriteriaColumn.DOMAIN_CONCEPT: "C.visit_concept_id",
            CriteriaColumn.DURATION: "DATEDIFF(day, C.visit_start_date, C.visit_end_date)",
            CriteriaColumn.VISIT_ID: "C.visit_occurrence_id",
            CriteriaColumn.AGE: "NULL",
            CriteriaColumn.GENDER: "NULL",
            CriteriaColumn.RACE: "NULL",
            CriteriaColumn.ETHNICITY: "NULL"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    def get_criteria_sql(self, criteria: VisitOccurrence, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for visit occurrence criteria."""
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
    
    def embed_codeset_clause(self, query: str, criteria: VisitOccurrence) -> str:
        """Embed codeset clause for visit occurrence criteria."""
        # VisitOccurrence doesn't have codeset_id field, so return query with empty codeset clause
        return query.replace("@codesetClause", "")
    
    def resolve_select_clauses(self, criteria: VisitOccurrence, options: BuilderOptions) -> str:
        """Resolve select clauses for visit occurrence criteria."""
        columns = list(self.get_default_columns())
        if options.additional_columns:
            columns.extend(options.additional_columns)
        
        select_parts = []
        for column in columns:
            table_column = self.get_table_column_for_criteria_column(column)
            select_parts.append(f"{table_column} as {column.value}")
        
        return ", ".join(select_parts)
    
    def resolve_join_clauses(self, criteria: VisitOccurrence, options: BuilderOptions) -> str:
        """Resolve join clauses for visit occurrence criteria."""
        joins = []
        
        # Add provider specialty join if needed
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            joins.append(f"""
            JOIN @cdm_database_schema.PROVIDER P ON C.provider_id = P.provider_id
            """)
        
        return " ".join(joins)
    
    def resolve_where_clauses(self, criteria: VisitOccurrence, options: BuilderOptions) -> str:
        """Resolve where clauses for visit occurrence criteria."""
        conditions = []
        
        # Add codeset condition
        codeset_clause = self.embed_codeset_clause("", criteria)
        if codeset_clause:
            conditions.append(codeset_clause)
        
        # Add date range conditions
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_start_date, "C.visit_start_date"
            )
            if date_clause:
                conditions.append(date_clause)
        
        if criteria.occurrence_end_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_end_date, "C.visit_end_date"
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
        
        # Add provider specialty condition
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            provider_clause = BuilderUtils.get_codeset_in_expression(
                criteria.provider_specialty_cs.codeset_id,
                "P.specialty_concept_id",
                criteria.provider_specialty_cs.is_exclusion
            )
            if provider_clause:
                conditions.append(provider_clause)
        
        return " AND ".join(conditions) if conditions else "1=1"
    
    def resolve_ordinal_expression(self, criteria: VisitOccurrence, options: BuilderOptions) -> str:
        """Resolve ordinal expression for visit occurrence criteria."""
        # VisitOccurrence doesn't have a 'first' field, so no ordering
        return ""
