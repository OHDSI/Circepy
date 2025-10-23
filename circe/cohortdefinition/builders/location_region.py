"""
Location Region SQL Builder

This module contains the SQL builder for Location Region criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import LocationRegion


class LocationRegionSqlBuilder(CriteriaSqlBuilder[LocationRegion]):
    """SQL builder for Location Region criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.LocationRegionSqlBuilder
    """
    
    # Default columns are those that are specified in the template, and don't need to be added if specified in 'additionalColumns'
    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.VISIT_ID
    }
    
    def get_query_template(self) -> str:
        """Get the SQL query template for location region criteria."""
        return """
        SELECT 
            @selectClause
        FROM (
            SELECT 
                l.location_id,
                l.region_concept_id,
                l.location_start_date,
                l.location_end_date
                @ordinalExpression
            FROM @cdm_database_schema.LOCATION l
            @codesetClause
        ) C
        @joinClause
        WHERE @whereClause
        @additionalColumns
        """
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for location region criteria."""
        return self.DEFAULT_COLUMNS
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DOMAIN_CONCEPT: "C.region_concept_id",
            CriteriaColumn.START_DATE: "C.start_date",
            CriteriaColumn.END_DATE: "C.end_date",
            CriteriaColumn.VISIT_ID: "NULL",
            CriteriaColumn.AGE: "NULL",
            CriteriaColumn.GENDER: "NULL",
            CriteriaColumn.RACE: "NULL",
            CriteriaColumn.ETHNICITY: "NULL"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    def embed_codeset_clause(self, query: str, criteria: LocationRegion) -> str:
        """Embed codeset clause in query."""
        codeset_clause = BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id,
            "l.region_concept_id",
            None,
            None
        )
        return query.replace("@codesetClause", codeset_clause)
    
    def embed_ordinal_expression(self, query: str, criteria: LocationRegion, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query."""
        return query.replace("@ordinalExpression", "")
    
    def resolve_join_clauses(self, criteria: LocationRegion, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for location region criteria."""
        return []
    
    def resolve_where_clauses(self, criteria: LocationRegion, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for location region criteria."""
        return []
