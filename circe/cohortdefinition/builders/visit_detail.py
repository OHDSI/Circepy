"""
Visit Detail SQL Builder

This module contains the SQL builder for Visit Detail criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import VisitDetail


class VisitDetailSqlBuilder(CriteriaSqlBuilder[VisitDetail]):
    """SQL builder for Visit Detail criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.VisitDetailSqlBuilder
    """
    
    # Default columns are those that are specified in the template, and don't need to be added if specified in 'additionalColumns'
    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.VISIT_DETAIL_ID
    }
    
    # Default select columns are the columns that will always be returned from the subquery, but are added to based on the specific criteria
    DEFAULT_SELECT_COLUMNS = [
        "vd.person_id",
        "vd.visit_detail_id", 
        "vd.visit_detail_concept_id",
        "vd.visit_occurrence_id"
    ]
    
    def get_query_template(self) -> str:
        """Get the SQL query template for visit detail criteria."""
        return """
        SELECT 
            @selectClause@additionalColumns
        FROM (
            SELECT 
                vd.person_id,
                vd.visit_detail_id,
                vd.visit_detail_concept_id,
                vd.visit_occurrence_id,
                vd.visit_detail_type_concept_id,
                vd.provider_id,
                vd.care_site_id,
                vd.visit_detail_start_date,
                vd.visit_detail_end_date
                @ordinalExpression
            FROM @cdm_database_schema.VISIT_DETAIL vd
            @codesetClause
        ) C
        @joinClause
        @whereClause
        @additionalColumns
        """
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for visit detail criteria."""
        return self.DEFAULT_COLUMNS
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DOMAIN_CONCEPT: "C.visit_detail_concept_id",
            CriteriaColumn.DURATION: "DATEDIFF(d, C.start_date, C.end_date)",
            CriteriaColumn.START_DATE: "C.start_date",
            CriteriaColumn.END_DATE: "C.end_date",
            CriteriaColumn.VISIT_DETAIL_ID: "C.visit_detail_id"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    def embed_codeset_clause(self, query: str, criteria: VisitDetail) -> str:
        """Embed codeset clause in query."""
        codeset_clause = BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id,
            "vd.visit_detail_concept_id",
            criteria.visit_detail_source_concept,
            "vd.visit_detail_source_concept_id"
        )
        return query.replace("@codesetClause", codeset_clause)
    
    def embed_ordinal_expression(self, query: str, criteria: VisitDetail, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query."""
        # first
        if criteria.first is not None and criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace("@ordinalExpression", ", row_number() over (PARTITION BY vd.person_id ORDER BY vd.visit_detail_start_date, vd.visit_detail_id) as ordinal")
        else:
            query = query.replace("@ordinalExpression", "")
        return query
    
    def resolve_select_clauses(self, criteria: VisitDetail, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for visit detail criteria."""
        select_cols = list(self.DEFAULT_SELECT_COLUMNS)
        
        # visitType
        if criteria.visit_detail_type_cs is not None:
            select_cols.append("vd.visit_detail_type_concept_id")
        
        # providerSpecialty
        if criteria.provider_specialty_cs is not None:
            select_cols.append("vd.provider_id")
        
        # placeOfService
        if criteria.place_of_service_cs is not None:
            select_cols.append("vd.care_site_id")
        
        # dateAdjustment or default start/end dates
        if criteria.date_adjustment is not None:
            start_column = "vd.visit_detail_start_date" if criteria.date_adjustment.start_with == "start_date" else "vd.visit_detail_end_date"
            end_column = "vd.visit_detail_start_date" if criteria.date_adjustment.end_with == "start_date" else "vd.visit_detail_end_date"
            select_cols.append(BuilderUtils.get_date_adjustment_expression(criteria.date_adjustment, start_column, end_column))
        else:
            select_cols.append("vd.visit_detail_start_date as start_date")
            select_cols.append("vd.visit_detail_end_date as end_date")
        
        # Add domain concept column
        select_cols.append("vd.visit_detail_concept_id as domain_concept")
        
        # Add visit_detail_id column
        select_cols.append("vd.visit_detail_id as visit_detail_id")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: VisitDetail, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for visit detail criteria."""
        join_clauses = []
        
        if criteria.age is not None or criteria.gender_cs is not None or criteria.gender is not None:  # join to PERSON
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        if criteria.place_of_service_cs is not None or criteria.place_of_service_location is not None:
            join_clauses.append("JOIN @cdm_database_schema.CARE_SITE CS on C.care_site_id = CS.care_site_id")
        
        if criteria.provider_specialty_cs is not None:
            join_clauses.append("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id")
        
        if criteria.place_of_service_location is not None:
            self.add_filtering_by_care_site_location_region(join_clauses, criteria.place_of_service_location)
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: VisitDetail, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for visit detail criteria."""
        where_clauses = []
        
        # occurrenceStartDate
        if criteria.visit_detail_start_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.start_date", criteria.visit_detail_start_date)
            if date_clause:
                where_clauses.append(date_clause)
        
        # occurrenceEndDate
        if criteria.visit_detail_end_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.end_date", criteria.visit_detail_end_date)
            if date_clause:
                where_clauses.append(date_clause)
        
        # visitType
        if criteria.visit_detail_type_cs is not None:
            self.add_where_clause(where_clauses, criteria.visit_detail_type_cs, "C.visit_detail_type_concept_id", criteria.visit_detail_type_exclude)
        
        # visitLength
        if criteria.visit_detail_length is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause("DATEDIFF(d,C.start_date, C.end_date)", criteria.visit_detail_length)
            if numeric_clause:
                where_clauses.append(numeric_clause)
        
        # age
        if criteria.age is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause("YEAR(C.end_date) - P.year_of_birth", criteria.age)
            if numeric_clause:
                where_clauses.append(numeric_clause)
        
        # gender
        if criteria.gender is not None and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            if concept_ids:
                where_clauses.append(f"P.gender_concept_id in ({','.join(map(str, concept_ids))})")
        
        if criteria.gender_cs is not None:
            self.add_where_clause(where_clauses, criteria.gender_cs, "P.gender_concept_id")
        
        # providerSpecialty
        if criteria.provider_specialty_cs is not None:
            self.add_where_clause(where_clauses, criteria.provider_specialty_cs, "PR.specialty_concept_id")
        
        # placeOfService
        if criteria.place_of_service_cs is not None:
            self.add_where_clause(where_clauses, criteria.place_of_service_cs, "CS.place_of_service_concept_id")
        
        return where_clauses
    
    def get_additional_columns(self, columns: List[CriteriaColumn]) -> str:
        """Get additional columns string with proper aliases.
        
        Java equivalent: VisitDetailSqlBuilder.getAdditionalColumns()
        """
        return ", ".join([f"{self.get_table_column_for_criteria_column(col)} as {col.value}" for col in columns])
    
    def add_filtering_by_care_site_location_region(self, join_clauses: List[str], codeset_id: int):
        """Add filtering by care site location region."""
        join_clauses.append(self.get_location_history_join("LH", "CARE_SITE", "C.care_site_id"))
        join_clauses.append("JOIN @cdm_database_schema.LOCATION LOC on LOC.location_id = LH.location_id")
        self.add_filtering(join_clauses, codeset_id, "LOC.region_concept_id")
    
    def add_where_clause(self, where_clauses: List[str], concept_set_selection, concept_column: str, exclude: Optional[bool] = None):
        """Add where clause for concept set selection."""
        is_exclusion = exclude if exclude is not None else concept_set_selection.is_exclusion
        codeset_clause = BuilderUtils.get_codeset_in_expression(
            concept_set_selection.codeset_id, 
            concept_column, 
            is_exclusion
        )
        if codeset_clause:
            where_clauses.append(codeset_clause)
    
    def add_filtering(self, join_clauses: List[str], codeset_id: int, standard_concept_column: str):
        """Add filtering join clause."""
        join_clauses.append(
            BuilderUtils.get_codeset_join_expression(
                codeset_id,
                standard_concept_column,
                None,
                None
            )
        )
    
    def get_location_history_join(self, alias: str, domain: str, entity_id_field: str) -> str:
        """Get location history join clause."""
        return f"""JOIN @cdm_database_schema.LOCATION_HISTORY {alias} 
            on {alias}.entity_id = {entity_id_field} 
            AND {alias}.domain_id = '{domain}' 
            AND C.visit_detail_start_date >= {alias}.start_date 
            AND C.visit_detail_end_date <= ISNULL({alias}.end_date, DATEFROMPARTS(2099,12,31))"""
