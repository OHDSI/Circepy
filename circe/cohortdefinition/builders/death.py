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
        return """
        SELECT C.person_id, C.death_date as start_date, C.death_date as end_date,
          C.death_type_concept_id as domain_concept@additionalColumns
        FROM 
        (
          SELECT @selectClause @ordinalExpression
          FROM @cdm_database_schema.DEATH C
          @codesetClause
        ) C
        @joinClause
        WHERE @whereClause
        @ordinalExpression
        """
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for death criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT
        }
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.START_DATE: "C.death_date",
            CriteriaColumn.END_DATE: "C.death_date",
            CriteriaColumn.DOMAIN_CONCEPT: "C.death_type_concept_id",
            CriteriaColumn.DURATION: "NULL",
            CriteriaColumn.VISIT_ID: "NULL",
            CriteriaColumn.AGE: "NULL",
            CriteriaColumn.GENDER: "NULL",
            CriteriaColumn.RACE: "NULL",
            CriteriaColumn.ETHNICITY: "NULL"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    
    def embed_codeset_clause(self, query: str, criteria: Death) -> str:
        """Embed codeset clause for death criteria."""
        if criteria.codeset_id is None:
            return query.replace("@codesetClause", "")
        
        codeset_clause = BuilderUtils.get_codeset_in_expression(
            criteria.codeset_id, 
            "C.death_concept_id",
            not criteria.death_type_exclude if hasattr(criteria, 'death_type_exclude') else False
        )
        return query.replace("@codesetClause", codeset_clause)
    
    def resolve_select_clauses(self, criteria: Death, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for death criteria."""
        return [
            "C.person_id",
            "C.death_date",
            "C.death_type_concept_id"
        ]
    
    def resolve_join_clauses(self, criteria: Death, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for death criteria."""
        # Death table typically doesn't need additional joins
        return []
    
    def resolve_where_clauses(self, criteria: Death, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for death criteria."""
        conditions = []
        
        # Add date range conditions
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_start_date, "C.death_date"
            )
            if date_clause:
                conditions.append(date_clause)
        
        if criteria.occurrence_end_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_end_date, "C.death_date"
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
        
        return conditions
    
    def embed_ordinal_expression(self, query: str, criteria: Death, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query."""
        if criteria.first:
            # Replace the first @ordinalExpression with row_number() function
            query = query.replace("@ordinalExpression", ", row_number() over (PARTITION BY C.person_id ORDER BY C.death_date, C.person_id) as ordinal", 1)
            # Replace the second @ordinalExpression with ORDER BY clause
            query = query.replace("@ordinalExpression", "ORDER BY C.death_date ASC")
            where_clauses.append("C.ordinal = 1")
        else:
            # Replace both @ordinalExpression placeholders with empty strings
            query = query.replace("@ordinalExpression", "")
            query = query.replace("@ordinalExpression", "")
        return query
