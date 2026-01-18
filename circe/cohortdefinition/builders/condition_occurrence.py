"""
Condition Occurrence SQL Builder

This module contains the SQL builder for condition occurrence criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import ConditionOccurrence


class ConditionOccurrenceSqlBuilder(CriteriaSqlBuilder[ConditionOccurrence]):
    """SQL builder for Condition Occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.ConditionOccurrenceSqlBuilder
    """
    
    # Default columns are those that are specified in the template, and don't need to be added if specified in 'additionalColumns'
    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.VISIT_ID
    }
    
    # Default select columns are the columns that will always be returned from the subquery, but are added to based on the specific criteria
    DEFAULT_SELECT_COLUMNS = [
        "co.person_id",
        "co.condition_occurrence_id", 
        "co.condition_concept_id",
        "co.visit_occurrence_id"
    ]
    
    def get_query_template(self) -> str:
        """Get the SQL query template for condition occurrence criteria."""
        return """
-- Begin Condition Occurrence Criteria
SELECT C.person_id, C.condition_occurrence_id as event_id, C.start_date, C.end_date,
  C.visit_occurrence_id, C.start_date as sort_date@additionalColumns
FROM 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.CONDITION_OCCURRENCE co
  @codesetClause
) C
@joinClause
@whereClause
-- End Condition Occurrence Criteria
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for condition occurrence criteria."""
        return self.DEFAULT_COLUMNS
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DOMAIN_CONCEPT: "C.condition_concept_id",
            CriteriaColumn.DURATION: "(DATEDIFF(d,C.start_date, C.end_date))",
            CriteriaColumn.START_DATE: "C.start_date",
            CriteriaColumn.END_DATE: "C.end_date",
            CriteriaColumn.VISIT_ID: "C.visit_occurrence_id"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    def embed_codeset_clause(self, query: str, criteria: ConditionOccurrence) -> str:
        """Embed codeset clause in query.
        
        Java equivalent: ConditionOccurrenceSqlBuilder.embedCodesetClause()
        """
        return query.replace("@codesetClause",
                           BuilderUtils.get_codeset_join_expression(
                               criteria.codeset_id,
                               "co.condition_concept_id",
                               criteria.condition_source_concept,
                               "co.condition_source_concept_id"
                           ))
    
    def embed_ordinal_expression(self, query: str, criteria: ConditionOccurrence, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query."""
        # first
        if criteria.first is not None and criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace("@ordinalExpression", ", row_number() over (PARTITION BY co.person_id ORDER BY co.condition_start_date, co.condition_occurrence_id) as ordinal")
        else:
            query = query.replace("@ordinalExpression", "")
        return query
    
    def resolve_select_clauses(self, criteria: ConditionOccurrence, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for condition occurrence criteria."""
        select_cols = list(self.DEFAULT_SELECT_COLUMNS)
        
        # Condition Type
        if ((criteria.condition_type is not None and len(criteria.condition_type) > 0) or
            criteria.condition_type_cs is not None):
            select_cols.append("co.condition_type_concept_id")
        
        # Stop Reason
        if criteria.stop_reason is not None:
            select_cols.append("co.stop_reason")
        
        # providerSpecialty
        if ((criteria.provider_specialty is not None and len(criteria.provider_specialty) > 0) or
            criteria.provider_specialty_cs is not None):
            select_cols.append("co.provider_id")
        
        # conditionStatus
        if ((criteria.condition_status is not None and len(criteria.condition_status) > 0) or
            criteria.condition_status_cs is not None):
            select_cols.append("co.condition_status_concept_id")
        
        # dateAdjustment or default start/end dates
        if criteria.date_adjustment is not None:
            start_column = "co.condition_start_date" if criteria.date_adjustment.start_with == "start_date" else "COALESCE(co.condition_end_date, DATEADD(day,1,co.condition_start_date))"
            end_column = "co.condition_start_date" if criteria.date_adjustment.end_with == "start_date" else "COALESCE(co.condition_end_date, DATEADD(day,1,co.condition_start_date))"
            select_cols.append(BuilderUtils.get_date_adjustment_expression(criteria.date_adjustment, start_column, end_column))
        else:
            select_cols.append("co.condition_start_date as start_date, COALESCE(co.condition_end_date, DATEADD(day,1,co.condition_start_date)) as end_date")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: ConditionOccurrence, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for condition occurrence criteria."""
        join_clauses = []
        
        # join to PERSON
        if (criteria.age is not None or 
            (criteria.gender is not None and len(criteria.gender) > 0) or
            criteria.gender_cs is not None):
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        # join to VISIT_OCCURRENCE
        if ((criteria.visit_type is not None and len(criteria.visit_type) > 0) or
            criteria.visit_type_cs is not None):
            join_clauses.append("JOIN @cdm_database_schema.VISIT_OCCURRENCE V on C.visit_occurrence_id = V.visit_occurrence_id and C.person_id = V.person_id")
        
        # join to PROVIDER
        if ((criteria.provider_specialty is not None and len(criteria.provider_specialty) > 0) or
            criteria.provider_specialty_cs is not None):
            join_clauses.append("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id")
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: ConditionOccurrence, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for condition occurrence criteria."""
        where_clauses = []
        
        # occurrenceStartDate
        if criteria.occurrence_start_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.start_date", criteria.occurrence_start_date)
            if date_clause:
                where_clauses.append(date_clause)
        
        # occurrenceEndDate
        if criteria.occurrence_end_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.end_date", criteria.occurrence_end_date)
            if date_clause:
                where_clauses.append(date_clause)
        
        # conditionType
        if criteria.condition_type is not None and len(criteria.condition_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.condition_type)
            if concept_ids:
                exclude_clause = "not" if criteria.condition_type_exclude else ""
                where_clauses.append(f"C.condition_type_concept_id {exclude_clause} in ({','.join(map(str, concept_ids))})")
        
        # conditionTypeCS
        if criteria.condition_type_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(criteria.condition_type_cs.codeset_id, "C.condition_type_concept_id", criteria.condition_type_cs.is_exclusion)
            if codeset_clause:
                where_clauses.append(codeset_clause)
        
        # Stop Reason
        if criteria.stop_reason is not None:
            text_clause = BuilderUtils.build_text_filter_clause(criteria.stop_reason, "C.stop_reason")
            if text_clause:
                where_clauses.append(text_clause)
        
        # age
        if criteria.age is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause("YEAR(C.start_date) - P.year_of_birth", criteria.age)
            if numeric_clause:
                where_clauses.append(numeric_clause)
        
        # gender
        if criteria.gender is not None and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            if concept_ids:
                where_clauses.append(f"P.gender_concept_id in ({','.join(map(str, concept_ids))})")
        
        # genderCS
        if criteria.gender_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(criteria.gender_cs.codeset_id, "P.gender_concept_id", criteria.gender_cs.is_exclusion)
            if codeset_clause:
                where_clauses.append(codeset_clause)
        
        # providerSpecialty
        if criteria.provider_specialty is not None and len(criteria.provider_specialty) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.provider_specialty)
            if concept_ids:
                where_clauses.append(f"PR.specialty_concept_id in ({','.join(map(str, concept_ids))})")
        
        # providerSpecialtyCS
        if criteria.provider_specialty_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(criteria.provider_specialty_cs.codeset_id, "PR.specialty_concept_id", criteria.provider_specialty_cs.is_exclusion)
            if codeset_clause:
                where_clauses.append(codeset_clause)
        
        # visitType
        if criteria.visit_type is not None and len(criteria.visit_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.visit_type)
            if concept_ids:
                where_clauses.append(f"V.visit_concept_id in ({','.join(map(str, concept_ids))})")
        
        # visitTypeCS
        if criteria.visit_type_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(criteria.visit_type_cs.codeset_id, "V.visit_concept_id", criteria.visit_type_cs.is_exclusion)
            if codeset_clause:
                where_clauses.append(codeset_clause)
        
        # conditionStatus
        if criteria.condition_status is not None and len(criteria.condition_status) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.condition_status)
            if concept_ids:
                where_clauses.append(f"C.condition_status_concept_id in ({','.join(map(str, concept_ids))})")
        
        # conditionStatusCS
        if criteria.condition_status_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(criteria.condition_status_cs.codeset_id, "C.condition_status_concept_id", criteria.condition_status_cs.is_exclusion)
            if codeset_clause:
                where_clauses.append(codeset_clause)
        
        return where_clauses