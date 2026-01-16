"""
Observation SQL Builder

This module contains the SQL builder for Observation criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import Observation


class ObservationSqlBuilder(CriteriaSqlBuilder[Observation]):
    """SQL builder for Observation criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.ObservationSqlBuilder
    """
    
    def get_query_template(self) -> str:
        """Get the SQL query template for observation criteria."""
        return """-- Begin Observation Criteria
SELECT C.person_id, C.observation_id as event_id, C.start_date, C.end_date,
       C.visit_occurrence_id, C.start_date as sort_date@additionalColumns
FROM 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.OBSERVATION o
@codesetClause
) C
@joinClause
@whereClause
-- End Observation Criteria
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for observation criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.VISIT_ID
        }
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.START_DATE: "C.start_date",
            CriteriaColumn.END_DATE: "C.end_date",
            CriteriaColumn.DOMAIN_CONCEPT: "C.observation_concept_id",
            CriteriaColumn.DURATION: "NULL",
            CriteriaColumn.VISIT_ID: "C.visit_occurrence_id"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    
    def embed_codeset_clause(self, query: str, criteria: Observation) -> str:
        """Embed codeset clause for observation criteria."""
        return query.replace("@codesetClause", BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id,
            "o.observation_concept_id",
            criteria.observation_source_concept,
            "o.observation_source_concept_id"
        ))
    
    def resolve_select_clauses(self, criteria: Observation, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for observation criteria.
        
        Java equivalent: ObservationSqlBuilder.resolveSelectClauses()
        """
        # Default select columns that are always returned from inner subquery
        select_cols = [
            "o.person_id",
            "o.observation_id", 
            "o.observation_concept_id",
            "o.visit_occurrence_id",
            "o.value_as_number",
            "o.value_as_string",
            "o.value_as_concept_id",
            "o.unit_concept_id"
        ]
        
        # observationType
        if (criteria.observation_type and len(criteria.observation_type) > 0) or criteria.observation_type_cs:
            select_cols.append("o.observation_type_concept_id")
            
        # qualifier
        if (criteria.qualifier and len(criteria.qualifier) > 0) or criteria.qualifier_cs:
             select_cols.append("o.qualifier_concept_id")
             
        # providerSpecialty
        if (criteria.provider_specialty and len(criteria.provider_specialty) > 0) or criteria.provider_specialty_cs:
             select_cols.append("o.provider_id")
        
        # Add date columns (start_date and end_date)
        select_cols.append("o.observation_date as start_date")
        select_cols.append("DATEADD(day,1,o.observation_date) as end_date")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: Observation, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for observation criteria.
        
        Java equivalent: ObservationSqlBuilder.resolveJoinClauses()
        """
        join_clauses = []
        
        # Join to PERSON if age or gender conditions are present
        if criteria.age or (criteria.gender and len(criteria.gender) > 0) or (criteria.gender_cs and criteria.gender_cs.codeset_id):
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        # Join to PROVIDER if provider specialty conditions are present
        # Always use PR alias for PROVIDER to match Java implementation
        if (criteria.provider_specialty and len(criteria.provider_specialty) > 0) or (criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id):
            join_clauses.append("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id")
        
        # Join to VISIT_OCCURRENCE if visit type conditions are present
        if (criteria.visit_type and len(criteria.visit_type) > 0) or (criteria.visit_type_cs and criteria.visit_type_cs.codeset_id):
            join_clauses.append("JOIN @cdm_database_schema.VISIT_OCCURRENCE V on C.visit_occurrence_id = V.visit_occurrence_id and C.person_id = V.person_id")
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: Observation, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for observation criteria."""
        where_clauses = super().resolve_where_clauses(criteria)
        
        # Add date range conditions
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                "C.start_date", criteria.occurrence_start_date
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        if criteria.occurrence_end_date:
            date_clause = BuilderUtils.build_date_range_clause(
                "C.end_date", criteria.occurrence_end_date
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        # observationType
        if criteria.observation_type and len(criteria.observation_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.observation_type)
            operator = "not in" if criteria.observation_type_exclude else "in"
            where_clauses.append(f"C.observation_type_concept_id {operator} ({','.join(map(str, concept_ids))})")
            
        # observationTypeCS
        if criteria.observation_type_cs:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.observation_type_cs.codeset_id, "C.observation_type_concept_id"))

        # valueAsNumber
        if hasattr(criteria, 'value_as_number') and criteria.value_as_number:
            where_clauses.append(BuilderUtils.build_numeric_range_clause("C.value_as_number", criteria.value_as_number, ".4f"))

        # valueAsString
        if criteria.value_as_string:
            where_clauses.append(BuilderUtils.build_text_filter_clause(criteria.value_as_string, "C.value_as_string"))

        # valueAsConcept
        if hasattr(criteria, 'value_as_concept') and criteria.value_as_concept and len(criteria.value_as_concept) > 0:
             concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.value_as_concept)
             where_clauses.append(f"C.value_as_concept_id in ({','.join(map(str, concept_ids))})")
             
        # valueAsConceptCS
        if hasattr(criteria, 'value_as_concept_cs') and criteria.value_as_concept_cs:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.value_as_concept_cs.codeset_id, "C.value_as_concept_id"))

        # unit
        if hasattr(criteria, 'unit') and criteria.unit and len(criteria.unit) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.unit)
            where_clauses.append(f"C.unit_concept_id in ({','.join(map(str, concept_ids))})")
        
        # unitCS
        if hasattr(criteria, 'unit_cs') and criteria.unit_cs:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.unit_cs.codeset_id, "C.unit_concept_id"))

        # qualifier
        if hasattr(criteria, 'qualifier') and criteria.qualifier and len(criteria.qualifier) > 0:
             concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.qualifier)
             where_clauses.append(f"C.qualifier_concept_id in ({','.join(map(str, concept_ids))})")
             
        # qualifierCS
        if hasattr(criteria, 'qualifier_cs') and criteria.qualifier_cs:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.qualifier_cs.codeset_id, "C.qualifier_concept_id"))

        # age
        if criteria.age:
            where_clauses.append(BuilderUtils.build_numeric_range_clause("YEAR(C.start_date) - P.year_of_birth", criteria.age))
            
        # gender
        if criteria.gender and len(criteria.gender) > 0:
             concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
             where_clauses.append(f"P.gender_concept_id in ({','.join(map(str, concept_ids))})")

        if criteria.gender_cs:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.gender_cs.codeset_id, "P.gender_concept_id", criteria.gender_cs.is_exclusion))
        
        # providerSpecialty
        if criteria.provider_specialty and len(criteria.provider_specialty) > 0:
             concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.provider_specialty)
             where_clauses.append(f"PR.specialty_concept_id in ({','.join(map(str, concept_ids))})")

        # providerSpecialtyCS
        if criteria.provider_specialty_cs:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.provider_specialty_cs.codeset_id, "PR.specialty_concept_id", criteria.provider_specialty_cs.is_exclusion))

        # visitType
        if criteria.visit_type and len(criteria.visit_type) > 0:
             concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.visit_type)
             where_clauses.append(f"V.visit_concept_id in ({','.join(map(str, concept_ids))})")
             
        # visitTypeCS
        if criteria.visit_type_cs:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.visit_type_cs.codeset_id, "V.visit_concept_id"))
        
        return where_clauses
    
    def get_additional_columns(self, columns: List[CriteriaColumn]) -> str:
        """Get additional columns string with proper aliases.
        
        Java equivalent: ObservationSqlBuilder.getAdditionalColumns()
        """
        return ", ".join([f"{self.get_table_column_for_criteria_column(col)} as {col.value}" for col in columns])
    
    def embed_ordinal_expression(self, query: str, criteria: Observation, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query."""
        # first
        if criteria.first is not None and criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace("@ordinalExpression", ", row_number() over (PARTITION BY o.person_id ORDER BY o.observation_date, o.observation_id) as ordinal")
        else:
            query = query.replace("@ordinalExpression", "")
        return query
    
    def resolve_ordinal_expression(self, criteria: Observation, options: BuilderOptions) -> str:
        """Resolve ordinal expression for observation criteria."""
        if criteria.first:
            return ", row_number() over (PARTITION BY o.person_id ORDER BY o.observation_date, o.observation_id) as ordinal"
        return ""
