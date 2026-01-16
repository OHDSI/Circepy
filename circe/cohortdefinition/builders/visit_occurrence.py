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
-- Begin Visit Occurrence Criteria
select C.person_id, C.visit_occurrence_id as event_id, C.start_date, C.end_date,
       C.visit_occurrence_id, C.start_date as sort_date@additionalColumns
from 
(
  select @selectClause @ordinalExpression
  FROM @cdm_database_schema.VISIT_OCCURRENCE vo
@codesetClause
) C
@joinClause
@whereClause
-- End Visit Occurrence Criteria
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for visit occurrence criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID
        }
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        if criteria_column == CriteriaColumn.DOMAIN_CONCEPT:
            return "C.visit_concept_id"
        elif criteria_column == CriteriaColumn.DURATION:
            return "DATEDIFF(d, C.start_date, C.end_date)"
        elif criteria_column == CriteriaColumn.START_DATE:
            return "C.start_date"
        elif criteria_column == CriteriaColumn.END_DATE:
            return "C.end_date"
        elif criteria_column == CriteriaColumn.VISIT_ID:
            return "C.visit_occurrence_id"
        else:
            raise ValueError(f"Invalid CriteriaColumn for Visit Occurrence: {criteria_column}")
    
    def embed_codeset_clause(self, query: str, criteria: VisitOccurrence) -> str:
        """Embed codeset clause for visit occurrence criteria."""
        codeset_clause = BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id,
            "vo.visit_concept_id",
            criteria.visit_source_concept,
            "vo.visit_source_concept_id"
        )
        return query.replace("@codesetClause", codeset_clause)
    
    def resolve_select_clauses(self, criteria: VisitOccurrence, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for visit occurrence criteria."""
        # Default select columns that are always returned
        select_cols = ["vo.person_id", "vo.visit_occurrence_id", "vo.visit_concept_id"]
        
        # visitType
        if ((criteria.visit_type and len(criteria.visit_type) > 0) or 
            (criteria.visit_type_cs and criteria.visit_type_cs.codeset_id)):
            select_cols.append("vo.visit_type_concept_id")
        
        # providerSpecialty
        if ((criteria.provider_specialty and len(criteria.provider_specialty) > 0) or 
            (criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id)):
            select_cols.append("vo.provider_id")
        
        # placeOfService
        if ((criteria.place_of_service and len(criteria.place_of_service) > 0) or
            (criteria.place_of_service_cs and criteria.place_of_service_cs.codeset_id)):
            select_cols.append("vo.care_site_id")
        
        # dateAdjustment or default start/end dates
        if criteria.date_adjustment:
            # Note: getDateAdjustmentExpression logic in Java-land:
            # BuilderUtils.getDateAdjustmentExpression(criteria.dateAdjustment,
            #   criteria.dateAdjustment.startWith == DateAdjustment.DateType.START_DATE ? "vo.visit_start_date" : "vo.visit_end_date",
            #   criteria.dateAdjustment.endWith == DateAdjustment.DateType.START_DATE ? "vo.visit_start_date" : "vo.visit_end_date")
            start_col = "vo.visit_start_date" if criteria.date_adjustment.start_with == "START_DATE" else "vo.visit_end_date"
            end_col = "vo.visit_start_date" if criteria.date_adjustment.end_with == "START_DATE" else "vo.visit_end_date"
            select_cols.append(BuilderUtils.get_date_adjustment_expression(criteria.date_adjustment, start_col, end_col))
        else:
            select_cols.append("vo.visit_start_date as start_date, vo.visit_end_date as end_date")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: VisitOccurrence, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for visit occurrence criteria."""
        join_clauses = []
        
        # Join to PERSON if age or gender conditions are present
        if (criteria.age or 
            (criteria.gender and len(criteria.gender) > 0) or
            (criteria.gender_cs and criteria.gender_cs.codeset_id)):
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        # Join to CARE_SITE if place of service conditions are present
        if ((criteria.place_of_service and len(criteria.place_of_service) > 0) or
            (criteria.place_of_service_cs and criteria.place_of_service_cs.codeset_id) or 
            criteria.place_of_service_location is not None):
            join_clauses.append("JOIN @cdm_database_schema.CARE_SITE CS on C.care_site_id = CS.care_site_id")
        
        # Join to PROVIDER if provider specialty conditions are present
        if ((criteria.provider_specialty and len(criteria.provider_specialty) > 0) or 
            (criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id)):
            join_clauses.append("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id")
        
        if criteria.place_of_service_location is not None:
            self._add_filtering_by_care_site_location_region(join_clauses, criteria.place_of_service_location)
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: VisitOccurrence, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for visit occurrence criteria."""
        where_clauses = super().resolve_where_clauses(criteria, options)
        
        # occurrenceStartDate
        if criteria.occurrence_start_date:
            where_clauses.append(BuilderUtils.build_date_range_clause("C.start_date", criteria.occurrence_start_date))
        
        # occurrenceEndDate
        if criteria.occurrence_end_date:
            where_clauses.append(BuilderUtils.build_date_range_clause("C.end_date", criteria.occurrence_end_date))
        
        # visitType
        if criteria.visit_type and len(criteria.visit_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.visit_type)
            exclude = "not " if criteria.visit_type_exclude else ""
            where_clauses.append(f"C.visit_type_concept_id {exclude}in ({','.join(map(str, concept_ids))})")

        # visitTypeCS
        if criteria.visit_type_cs and criteria.visit_type_cs.codeset_id:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(
                criteria.visit_type_cs.codeset_id, "C.visit_type_concept_id", criteria.visit_type_cs.is_exclusion
            ))
        
        # visitLength
        if criteria.visit_length:
            where_clauses.append(BuilderUtils.build_numeric_range_clause(
                "DATEDIFF(d,C.start_date, C.end_date)", criteria.visit_length
            ))
        
        # age
        if criteria.age:
            where_clauses.append(BuilderUtils.build_numeric_range_clause(
                "YEAR(C.start_date) - P.year_of_birth", criteria.age
            ))
        
        # gender
        if criteria.gender and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            where_clauses.append(f"P.gender_concept_id in ({','.join(map(str, concept_ids))})")

        # genderCS
        if criteria.gender_cs and criteria.gender_cs.codeset_id:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(
                criteria.gender_cs.codeset_id, "P.gender_concept_id", criteria.gender_cs.is_exclusion
            ))
        
        # providerSpecialty
        if criteria.provider_specialty and len(criteria.provider_specialty) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.provider_specialty)
            where_clauses.append(f"PR.specialty_concept_id in ({','.join(map(str, concept_ids))})")

        # providerSpecialtyCS
        if criteria.provider_specialty_cs and criteria.provider_specialty_cs.codeset_id:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(
                criteria.provider_specialty_cs.codeset_id, "PR.specialty_concept_id", criteria.provider_specialty_cs.is_exclusion
            ))
        
        # placeOfService
        if criteria.place_of_service and len(criteria.place_of_service) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.place_of_service)
            where_clauses.append(f"CS.place_of_service_concept_id in ({','.join(map(str, concept_ids))})")

        # placeOfServiceCS
        if criteria.place_of_service_cs and criteria.place_of_service_cs.codeset_id:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(
                criteria.place_of_service_cs.codeset_id, "CS.place_of_service_concept_id", criteria.place_of_service_cs.is_exclusion
            ))
        
        return where_clauses
        
        return where_clauses
    
    def embed_ordinal_expression(self, query: str, criteria: VisitOccurrence, where_clauses: List[str]) -> str:
        """Embed ordinal expression for visit occurrence criteria."""
        if criteria.first is not None and criteria.first:
            where_clauses.append("C.ordinal = 1")
            ordinal_expr = ", row_number() over (PARTITION BY vo.person_id ORDER BY vo.visit_start_date, vo.visit_occurrence_id) as ordinal"
            return query.replace("@ordinalExpression", ordinal_expr)
        else:
            return query.replace("@ordinalExpression", "")

    def _add_filtering_by_care_site_location_region(self, join_clauses: List[str], codeset_id: int):
        """Add joins for filtering by care site location region."""
        join_clauses.append(self._get_location_history_join("LH", "CARE_SITE", "C.care_site_id"))
        join_clauses.append("JOIN @cdm_database_schema.LOCATION LOC on LOC.location_id = LH.location_id")
        join_clauses.append(
            BuilderUtils.get_codeset_join_expression(
                codeset_id,
                "LOC.region_concept_id",
                None,
                None
            )
        )

    def _get_location_history_join(self, alias: str, domain: str, entity_id_field: str) -> str:
        """Get location history join expression."""
        return ("JOIN @cdm_database_schema.LOCATION_HISTORY " + alias + " "
                + "on " + alias + ".entity_id = " + entity_id_field + " "
                + "AND " + alias + ".domain_id = '" + domain + "' "
                + "AND C.visit_start_date >= " + alias + ".start_date "
                + "AND C.visit_end_date <= ISNULL(" + alias + ".end_date, DATEFROMPARTS(2099,12,31))")
