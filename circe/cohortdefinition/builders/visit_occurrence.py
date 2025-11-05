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
            @selectClause@additionalColumns
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
    
    
    def embed_codeset_clause(self, query: str, criteria: VisitOccurrence) -> str:
        """Embed codeset clause for visit occurrence criteria.
        
        Java equivalent: VisitOccurrenceSqlBuilder.embedCodesetClause()
        """
        codeset_clause = BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id,
            "C.visit_concept_id",
            criteria.visit_source_concept,
            "C.visit_source_concept_id"
        )
        return query.replace("@codesetClause", codeset_clause)
    
    def resolve_select_clauses(self, criteria: VisitOccurrence, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for visit occurrence criteria.
        
        Java equivalent: VisitOccurrenceSqlBuilder.resolveSelectClauses()
        """
        # Default select columns that are always returned
        select_cols = [
            "C.person_id",
            "C.visit_occurrence_id", 
            "C.visit_concept_id"
        ]
        
        # Add visit type column if needed
        if criteria.visit_type_cs and criteria.visit_type_cs.codeset_id:
            select_cols.append("C.visit_type_concept_id")
        
        # Add provider specialty column if needed
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            select_cols.append("C.provider_id")
        
        # Add place of service column if needed
        if criteria.place_of_service_cs and criteria.place_of_service_cs.codeset_id:
            select_cols.append("C.care_site_id")
        
        # Add date columns (start_date and end_date)
        select_cols.append("C.visit_start_date as start_date")
        select_cols.append("C.visit_end_date as end_date")
        
        # Add domain concept column
        select_cols.append("C.visit_concept_id as domain_concept")
        
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
    
    def resolve_join_clauses(self, criteria: VisitOccurrence, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for visit occurrence criteria.
        
        Java equivalent: VisitOccurrenceSqlBuilder.resolveJoinClauses()
        """
        join_clauses = []
        
        # Join to PERSON if age or gender conditions are present
        if criteria.age or (criteria.gender_cs and criteria.gender_cs.codeset_id):
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        # Join to CARE_SITE if place of service conditions are present
        if (criteria.place_of_service_cs and criteria.place_of_service_cs.codeset_id) or criteria.place_of_service_location:
            join_clauses.append("JOIN @cdm_database_schema.CARE_SITE CS on C.care_site_id = CS.care_site_id")
        
        # Join to PROVIDER if provider specialty conditions are present
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            join_clauses.append("JOIN @cdm_database_schema.PROVIDER P on C.provider_id = P.provider_id")
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: VisitOccurrence, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for visit occurrence criteria.
        
        Java equivalent: VisitOccurrenceSqlBuilder.resolveWhereClauses()
        """
        where_clauses = []
        
        # Add occurrence start date condition
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_start_date, "C.visit_start_date"
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        # Add occurrence end date condition
        if criteria.occurrence_end_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_end_date, "C.visit_end_date"
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        # Add visit type condition
        if criteria.visit_type_cs and criteria.visit_type_cs.codeset_id:
            visit_type_clause = BuilderUtils.get_codeset_in_expression(
                criteria.visit_type_cs.codeset_id,
                "C.visit_type_concept_id",
                criteria.visit_type_cs.is_exclusion
            )
            if visit_type_clause:
                where_clauses.append(visit_type_clause)
        
        # Add visit length condition
        if criteria.visit_length:
            length_clause = BuilderUtils.build_numeric_range_clause(
                criteria.visit_length, "DATEDIFF(d,C.visit_start_date, C.visit_end_date)"
            )
            if length_clause:
                where_clauses.append(length_clause)
        
        # Add age condition
        if criteria.age:
            age_clause = BuilderUtils.build_numeric_range_clause(
                criteria.age, "YEAR(C.visit_start_date) - P.year_of_birth"
            )
            if age_clause:
                where_clauses.append(age_clause)
                # Add person_id check for join requirement
                where_clauses.append("C.person_id = P.person_id")
        
        # Add gender condition
        if criteria.gender_cs and criteria.gender_cs.codeset_id:
            gender_clause = BuilderUtils.get_codeset_in_expression(
                criteria.gender_cs.codeset_id,
                "P.gender_concept_id",
                criteria.gender_cs.is_exclusion
            )
            if gender_clause:
                where_clauses.append(gender_clause)
        
        # Add provider specialty condition
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            provider_clause = BuilderUtils.get_codeset_in_expression(
                criteria.provider_specialty_cs.codeset_id,
                "P.specialty_concept_id",
                criteria.provider_specialty_cs.is_exclusion
            )
            if provider_clause:
                where_clauses.append(provider_clause)
        
        # Add place of service condition
        if criteria.place_of_service_cs and criteria.place_of_service_cs.codeset_id:
            place_clause = BuilderUtils.get_codeset_in_expression(
                criteria.place_of_service_cs.codeset_id,
                "CS.place_of_service_concept_id",
                criteria.place_of_service_cs.is_exclusion
            )
            if place_clause:
                where_clauses.append(place_clause)
        
        return where_clauses if where_clauses else ["1=1"]
    
    def get_additional_columns(self, columns: List[CriteriaColumn]) -> str:
        """Get additional columns string with proper aliases.
        
        Java equivalent: VisitOccurrenceSqlBuilder.getAdditionalColumns()
        """
        return ", ".join([f"{self.get_table_column_for_criteria_column(col)} as {col.value}" for col in columns])
    
    def resolve_ordinal_expression(self, criteria: VisitOccurrence, options: Optional[BuilderOptions] = None) -> str:
        """Resolve ordinal expression for visit occurrence criteria.
        
        Java equivalent: VisitOccurrenceSqlBuilder.resolveOrdinalExpression()
        """
        if criteria.first:
            return "ORDER BY C.visit_start_date ASC"
        return ""
    
    def embed_ordinal_expression(self, query: str, criteria: VisitOccurrence, where_clauses: List[str]) -> str:
        """Embed ordinal expression for visit occurrence criteria.
        
        Java equivalent: VisitOccurrenceSqlBuilder.embedOrdinalExpression()
        """
        # Check if first=True
        if criteria.first is not None and criteria.first:
            where_clauses.append("C.ordinal = 1")
            ordinal_expr = ", row_number() over (PARTITION BY C.person_id ORDER BY C.visit_start_date, C.visit_occurrence_id) as ordinal"
            return query.replace("@ordinalExpression", ordinal_expr)
        else:
            return query.replace("@ordinalExpression", "")
