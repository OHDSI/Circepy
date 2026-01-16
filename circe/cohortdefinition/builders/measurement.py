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
        return """-- Begin Measurement Criteria
SELECT C.person_id, C.measurement_id as event_id, C.start_date, C.end_date,
       C.visit_occurrence_id, C.start_date as sort_date@additionalColumns
from 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.MEASUREMENT m
@codesetClause
) C
@joinClause
@whereClause
-- End Measurement Criteria
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
            CriteriaColumn.START_DATE: "C.start_date",
            CriteriaColumn.END_DATE: "C.end_date",
            CriteriaColumn.DOMAIN_CONCEPT: "C.measurement_concept_id",
            CriteriaColumn.DURATION: "NULL",
            CriteriaColumn.VISIT_ID: "C.visit_occurrence_id"
        }
        return column_mapping.get(criteria_column, "NULL")

    def embed_ordinal_expression(self, query: str, criteria: Measurement, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query.
        
        Java equivalent: MeasurementSqlBuilder.embedOrdinalExpression()
        """
        # first
        if criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace("@ordinalExpression", ", row_number() over (PARTITION BY m.person_id ORDER BY m.measurement_date, m.measurement_id) as ordinal")
        else:
            query = query.replace("@ordinalExpression", "")
        
        return query
    
    def embed_codeset_clause(self, query: str, criteria: Measurement) -> str:
        """Embed codeset clause for measurement criteria."""
        return query.replace("@codesetClause", BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id,
            "m.measurement_concept_id",
            criteria.measurement_source_concept,
            "m.measurement_source_concept_id"
        ))
    
    def resolve_select_clauses(self, criteria: Measurement, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for measurement criteria.
        
        Java equivalent: MeasurementSqlBuilder.resolveSelectClauses()
        """
        # Default select columns that are always returned from inner subquery
        select_cols = [
            "m.person_id",
            "m.measurement_id", 
            "m.measurement_concept_id",
            "m.visit_occurrence_id",
            "m.value_as_number",
            "m.range_high",
            "m.range_low"
        ]
        
        # measurementType
        if (criteria.measurement_type and len(criteria.measurement_type) > 0) or criteria.measurement_type_cs:
            select_cols.append("m.measurement_type_concept_id")
            
        # operator
        if (criteria.operator and len(criteria.operator) > 0) or criteria.operator_cs:
             select_cols.append("m.operator_concept_id")
             
        # valueAsConcept
        if (criteria.value_as_concept and len(criteria.value_as_concept) > 0) or criteria.value_as_concept_cs:
             select_cols.append("m.value_as_concept_id")

        # unit
        if (criteria.unit and len(criteria.unit) > 0) or criteria.unit_cs:
            select_cols.append("m.unit_concept_id")
            
        # providerSpecialty
        if (criteria.provider_specialty and len(criteria.provider_specialty) > 0) or criteria.provider_specialty_cs:
             select_cols.append("m.provider_id")
        
        # dateAdjustment or default start/end dates
        if criteria.date_adjustment:
            select_cols.append(BuilderUtils.get_date_adjustment_expression(
                criteria.date_adjustment,
                "m.measurement_date" if criteria.date_adjustment.start_with == "start_date" else "DATEADD(day,1,m.measurement_date)",
                "m.measurement_date" if criteria.date_adjustment.end_with == "start_date" else "DATEADD(day,1,m.measurement_date)"
            ))
        else:
            select_cols.append("m.measurement_date as start_date, DATEADD(day,1,m.measurement_date) as end_date")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: Measurement, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for measurement criteria.
        
        Java equivalent: MeasurementSqlBuilder.resolveJoinClauses()
        """
        join_clauses = []
        
        # Join to PERSON if age or gender conditions are present
        if criteria.age or (criteria.gender and len(criteria.gender) > 0) or (criteria.gender_cs and criteria.gender_cs.codeset_id):
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        # Join to VISIT_OCCURRENCE
        if (criteria.visit_type and len(criteria.visit_type) > 0) or (criteria.visit_type_cs and criteria.visit_type_cs.codeset_id):
             join_clauses.append("JOIN @cdm_database_schema.VISIT_OCCURRENCE V on C.visit_occurrence_id = V.visit_occurrence_id and C.person_id = V.person_id")

        # Join to PROVIDER if provider specialty conditions are present
        # Use "PR" alias to avoid conflict with PERSON alias
        if (criteria.provider_specialty and len(criteria.provider_specialty) > 0) or (criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id):
            join_clauses.append("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id")
        
        return join_clauses

    def resolve_ordinal_expression(self, criteria: Measurement, options: Optional[BuilderOptions] = None) -> str:
        """Resolve ordinal expression for measurement criteria."""
        if criteria.first:
            return "ORDER BY m.measurement_date, m.measurement_id ASC"
        return ""
    
    def resolve_where_clauses(self, criteria: Measurement, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for measurement criteria.
        
        Java equivalent: MeasurementSqlBuilder.resolveWhereClauses()
        """
        where_clauses = super().resolve_where_clauses(criteria)
        
        # Note: codeset filtering is now handled via JOIN in inner query, not WHERE clause
        
        # Add occurrence start date condition
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                "C.start_date", criteria.occurrence_start_date
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        # measurementType
        if criteria.measurement_type and len(criteria.measurement_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.measurement_type)
            operator = "not in" if criteria.measurement_type_exclude else "in"
            where_clauses.append(f"C.measurement_type_concept_id {operator} ({','.join(map(str, concept_ids))})")
            
        # measurementTypeCS
        if criteria.measurement_type_cs:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.measurement_type_cs.codeset_id, "C.measurement_type_concept_id"))

        # operator
        if criteria.operator and len(criteria.operator) > 0:
             concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.operator)
             where_clauses.append(f"C.operator_concept_id in ({','.join(map(str, concept_ids))})")
             
        # operatorCS
        if criteria.operator_cs:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.operator_cs.codeset_id, "C.operator_concept_id"))

        # valueAsNumber
        if criteria.value_as_number:
            # Java uses .4f
            where_clauses.append(BuilderUtils.build_numeric_range_clause("C.value_as_number", criteria.value_as_number, ".4f"))

        # valueAsConcept
        if criteria.value_as_concept and len(criteria.value_as_concept) > 0:
             concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.value_as_concept)
             where_clauses.append(f"C.value_as_concept_id in ({','.join(map(str, concept_ids))})")
             
        # valueAsConceptCS
        if criteria.value_as_concept_cs:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.value_as_concept_cs.codeset_id, "C.value_as_concept_id"))

        # unit
        if criteria.unit and len(criteria.unit) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.unit)
            where_clauses.append(f"C.unit_concept_id in ({','.join(map(str, concept_ids))})")
        
        # unitCS
        if criteria.unit_cs:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.unit_cs.codeset_id, "C.unit_concept_id"))
            
        # rangeLow
        if criteria.range_low:
             where_clauses.append(BuilderUtils.build_numeric_range_clause("C.range_low", criteria.range_low, ".4f"))
             
        # rangeHigh
        if criteria.range_high:
             where_clauses.append(BuilderUtils.build_numeric_range_clause("C.range_high", criteria.range_high, ".4f"))

        # rangeLowRatio
        if criteria.range_low_ratio:
             where_clauses.append(BuilderUtils.build_numeric_range_clause("(C.value_as_number / NULLIF(C.range_low, 0))", criteria.range_low_ratio, ".4f"))

        # rangeHighRatio
        if criteria.range_high_ratio:
             where_clauses.append(BuilderUtils.build_numeric_range_clause("(C.value_as_number / NULLIF(C.range_high, 0))", criteria.range_high_ratio, ".4f"))
             
        # abnormal
        if criteria.abnormal:
             where_clauses.append("(C.value_as_number < C.range_low or C.value_as_number > C.range_high or C.value_as_concept_id in (4155142, 4155143))")

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
        
        Java equivalent: MeasurementSqlBuilder.getAdditionalColumns()
        """
        return ", ".join([f"{self.get_table_column_for_criteria_column(col)} as {col.value}" for col in columns])
