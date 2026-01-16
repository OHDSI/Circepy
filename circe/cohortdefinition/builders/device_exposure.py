"""
Device Exposure SQL Builder

This module contains the SQL builder for Device Exposure criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import DeviceExposure


class DeviceExposureSqlBuilder(CriteriaSqlBuilder[DeviceExposure]):
    """SQL builder for Device Exposure criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.DeviceExposureSqlBuilder
    """
    
    def get_query_template(self) -> str:
        """Get the SQL query template for device exposure criteria."""
        return """-- Begin Device Exposure Criteria
SELECT C.person_id, C.device_exposure_id as event_id, C.start_date, C.end_date,
       C.visit_occurrence_id, C.start_date as sort_date@additionalColumns
FROM 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.DEVICE_EXPOSURE de
@codesetClause
) C
@joinClause
@whereClause
-- End Device Exposure Criteria"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for device exposure criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID
        }
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.START_DATE: "C.start_date",
            CriteriaColumn.END_DATE: "C.end_date",
            CriteriaColumn.DOMAIN_CONCEPT: "C.device_concept_id",
            CriteriaColumn.DURATION: "DATEDIFF(day, C.start_date, C.end_date)",
            CriteriaColumn.VISIT_ID: "C.visit_occurrence_id",
            CriteriaColumn.QUANTITY: "C.quantity"
        }
        return column_mapping.get(criteria_column, "NULL")
        
    def resolve_select_clauses(self, criteria: DeviceExposure, options: BuilderOptions) -> List[str]:
        """Resolve select clauses for device exposure criteria."""
        select_cols = [
            "de.person_id",
            "de.device_exposure_id",
            "de.device_concept_id",
            "de.visit_occurrence_id",
            "de.quantity"
        ]
        
        # Device Type
        if (criteria.device_type and len(criteria.device_type) > 0) or \
           (criteria.device_type_cs and criteria.device_type_cs.codeset_id):
            select_cols.append("de.device_type_concept_id")

        # unique_device_id
        if criteria.unique_device_id:
            select_cols.append("de.unique_device_id")

        # providerSpecialty
        if (criteria.provider_specialty and len(criteria.provider_specialty) > 0) or \
           (criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id):
            select_cols.append("de.provider_id")
            
        # dateAdjustment or default start/end dates
        if criteria.date_adjustment:
            select_cols.append(BuilderUtils.get_date_adjustment_expression(
                criteria.date_adjustment,
                "de.device_exposure_start_date" if criteria.date_adjustment.start_with == "START_DATE" else "COALESCE(de.device_exposure_end_date, DATEADD(day,1,de.device_exposure_start_date))",
                "de.device_exposure_start_date" if criteria.date_adjustment.end_with == "START_DATE" else "COALESCE(de.device_exposure_end_date, DATEADD(day,1,de.device_exposure_start_date))"
            ))
        else:
            select_cols.append("de.device_exposure_start_date as start_date, COALESCE(de.device_exposure_end_date, DATEADD(day,1,de.device_exposure_start_date)) as end_date")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: DeviceExposure, options: BuilderOptions) -> List[str]:
        """Resolve join clauses for device exposure criteria."""
        joins = []
        
        # Join to PERSON
        if criteria.age or \
           (criteria.gender and len(criteria.gender) > 0) or \
           (criteria.gender_cs and criteria.gender_cs.codeset_id):
            joins.append("JOIN @cdm_database_schema.PERSON P ON C.person_id = P.person_id")
            
        # Join to VISIT_OCCURRENCE
        if (criteria.visit_type and len(criteria.visit_type) > 0) or \
           (criteria.visit_type_cs and criteria.visit_type_cs.codeset_id):
            joins.append("JOIN @cdm_database_schema.VISIT_OCCURRENCE V ON C.visit_occurrence_id = V.visit_occurrence_id AND C.person_id = V.person_id")

        # Join to PROVIDER
        if (criteria.provider_specialty and len(criteria.provider_specialty) > 0) or \
           (criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id):
            joins.append("LEFT JOIN @cdm_database_schema.PROVIDER PR ON C.provider_id = PR.provider_id")
        
        return joins
    
    def embed_codeset_clause(self, query: str, criteria: DeviceExposure) -> str:
        """Embed codeset clause for device exposure criteria."""
        return query.replace("@codesetClause", BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id, 
            "de.device_concept_id",
            criteria.device_source_concept,
            "de.device_source_concept_id"
        ))
        
    def resolve_where_clauses(self, criteria: DeviceExposure, options: BuilderOptions) -> List[str]:
        """Resolve where clauses for device exposure criteria."""
        conditions = []
        
        # Add date range conditions
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                "C.start_date", criteria.occurrence_start_date
            )
            if date_clause:
                conditions.append(date_clause)
        
        if criteria.occurrence_end_date:
            date_clause = BuilderUtils.build_date_range_clause(
                "C.end_date", criteria.occurrence_end_date
            )
            if date_clause:
                conditions.append(date_clause)
        
        # deviceType
        if criteria.device_type and len(criteria.device_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.device_type)
            op = "NOT IN" if criteria.device_type_exclude else "IN"
            conditions.append(f"C.device_type_concept_id {op} ({','.join(map(str, concept_ids))})")
            
        # deviceTypeCS
        if criteria.device_type_cs and criteria.device_type_cs.codeset_id:
             conditions.append(BuilderUtils.get_codeset_in_expression(
                criteria.device_type_cs.codeset_id,
                "C.device_type_concept_id"
            ))

        # Add unique device ID condition
        if criteria.unique_device_id:
            device_id_clause = BuilderUtils.build_text_filter_clause(
                criteria.unique_device_id, "C.unique_device_id"
            )
            if device_id_clause:
                conditions.append(device_id_clause)
        
        # Add quantity condition
        if criteria.quantity:
            quantity_clause = BuilderUtils.build_numeric_range_clause(
                "C.quantity", criteria.quantity
            )
            if quantity_clause:
                conditions.append(quantity_clause)
                
        # Age
        if criteria.age:
            conditions.append(BuilderUtils.build_numeric_range_clause(
                "YEAR(C.start_date) - P.year_of_birth", criteria.age
            ))

        # Gender
        if criteria.gender and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            conditions.append(f"P.gender_concept_id IN ({','.join(map(str, concept_ids))})")
            
        # GenderCS
        if criteria.gender_cs and criteria.gender_cs.codeset_id:
             conditions.append(BuilderUtils.get_codeset_in_expression(
                criteria.gender_cs.codeset_id,
                "P.gender_concept_id"
            ))
            
        # Provider Specialty
        if criteria.provider_specialty and len(criteria.provider_specialty) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.provider_specialty)
            conditions.append(f"PR.specialty_concept_id IN ({','.join(map(str, concept_ids))})")
            
        # Provider Specialty CS
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
             conditions.append(BuilderUtils.get_codeset_in_expression(
                criteria.provider_specialty_cs.codeset_id,
                "PR.specialty_concept_id"
            ))

        # Visit Type
        if criteria.visit_type and len(criteria.visit_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.visit_type)
            conditions.append(f"V.visit_concept_id IN ({','.join(map(str, concept_ids))})")
            
        # Visit Type CS
        if criteria.visit_type_cs and criteria.visit_type_cs.codeset_id:
             conditions.append(BuilderUtils.get_codeset_in_expression(
                criteria.visit_type_cs.codeset_id,
                "V.visit_concept_id"
            ))
        
        return conditions
    
    def resolve_ordinal_expression(self, criteria: DeviceExposure, options: BuilderOptions) -> str:
        """Resolve ordinal expression for device exposure criteria."""
        if criteria.first:
            return ", row_number() over (PARTITION BY de.person_id ORDER BY de.device_exposure_start_date, de.device_exposure_id) as ordinal"
        return ""
    
    def get_ordinal_expression_where_clause(self, criteria: DeviceExposure, options: BuilderOptions) -> List[str]:
         if criteria.first:
             return ["C.ordinal = 1"]
         return []
