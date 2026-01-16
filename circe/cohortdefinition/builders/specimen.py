"""
Specimen SQL Builder

This module contains the SQL builder for Specimen criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import Specimen


class SpecimenSqlBuilder(CriteriaSqlBuilder[Specimen]):
    """SQL builder for Specimen criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.SpecimenSqlBuilder
    """
    
    def get_query_template(self) -> str:
        """Get the SQL query template for specimen criteria."""
        return """-- Begin Specimen Criteria
SELECT C.person_id, C.specimen_id as event_id, C.specimen_date as start_date, C.specimen_date as end_date,
       C.visit_occurrence_id, C.specimen_date as sort_date@additionalColumns
FROM 
(
  SELECT s.person_id, s.specimen_id, s.specimen_concept_id, s.specimen_date, s.visit_occurrence_id, s.quantity, s.unit_concept_id, s.anatomic_site_concept_id, s.disease_status_concept_id, s.specimen_source_id@selectClause @ordinalExpression
  FROM @cdm_database_schema.SPECIMEN s
  @codesetClause
) C
@joinClause
@whereClause
-- End Specimen Criteria
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for specimen criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID
        }
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DOMAIN_CONCEPT: "C.specimen_concept_id",
            CriteriaColumn.DURATION: "CAST(1 as int)",
            CriteriaColumn.START_DATE: "C.specimen_date",
            CriteriaColumn.END_DATE: "C.specimen_date",
            CriteriaColumn.VISIT_ID: "C.visit_occurrence_id",
            CriteriaColumn.QUANTITY: "C.quantity",
            CriteriaColumn.UNIT: "C.unit_concept_id"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    def embed_codeset_clause(self, query: str, criteria: Specimen) -> str:
        """Embed codeset clause for specimen criteria."""
        return query.replace("@codesetClause", BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id,
            "s.specimen_concept_id",
            criteria.specimen_source_concept,
            "s.specimen_source_concept_id"
        ))
    
    def embed_ordinal_expression(self, query: str, criteria: Specimen, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query."""
        if criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace("@ordinalExpression", ", row_number() over (PARTITION BY s.person_id ORDER BY s.specimen_date, s.specimen_id) as ordinal")
        else:
            query = query.replace("@ordinalExpression", "")
        return query

    def resolve_join_clauses(self, criteria: Specimen, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for specimen criteria."""
        joins = []
        
        # join to PERSON
        if (criteria.age or 
           (criteria.gender and len(criteria.gender) > 0) or 
           (criteria.gender_cs and criteria.gender_cs.codeset_id)):
            joins.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
            
        return joins
    
    def resolve_where_clauses(self, criteria: Specimen, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for specimen criteria."""
        where_clauses = []
        
        # occurrenceStartDate
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                "C.specimen_date", criteria.occurrence_start_date
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        # specimenType
        if criteria.specimen_type and len(criteria.specimen_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.specimen_type)
            op = "not in" if criteria.specimen_type_exclude else "in"
            where_clauses.append(f"C.specimen_type_concept_id {op} ({','.join(map(str, concept_ids))})")
            
        # specimenTypeCS
        if criteria.specimen_type_cs and criteria.specimen_type_cs.codeset_id:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.specimen_type_cs.codeset_id, "C.specimen_type_concept_id"))

        # quantity
        if criteria.quantity:
            where_clauses.append(BuilderUtils.build_numeric_range_clause("C.quantity", criteria.quantity, ".4f"))

        # unit
        if criteria.unit and len(criteria.unit) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.unit)
            where_clauses.append(f"C.unit_concept_id in ({','.join(map(str, concept_ids))})")
            
        # unitCS
        if criteria.unit_cs and criteria.unit_cs.codeset_id:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.unit_cs.codeset_id, "C.unit_concept_id"))

        # anatomicSite
        if criteria.anatomic_site and len(criteria.anatomic_site) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.anatomic_site)
            where_clauses.append(f"C.anatomic_site_concept_id in ({','.join(map(str, concept_ids))})")
            
        # anatomicSiteCS
        if criteria.anatomic_site_cs and criteria.anatomic_site_cs.codeset_id:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.anatomic_site_cs.codeset_id, "C.anatomic_site_concept_id"))

        # diseaseStatus
        if criteria.disease_status and len(criteria.disease_status) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.disease_status)
            where_clauses.append(f"C.disease_status_concept_id in ({','.join(map(str, concept_ids))})")
            
        # diseaseStatusCS
        if criteria.disease_status_cs and criteria.disease_status_cs.codeset_id:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.disease_status_cs.codeset_id, "C.disease_status_concept_id"))

        # sourceId
        if criteria.source_id:
            where_clauses.append(BuilderUtils.build_text_filter_clause(criteria.source_id, "C.specimen_source_id"))

        # age
        if criteria.age:
            where_clauses.append(BuilderUtils.build_numeric_range_clause(
                "YEAR(C.specimen_date) - P.year_of_birth", criteria.age
            ))
            
        # gender
        if criteria.gender and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            where_clauses.append(f"P.gender_concept_id in ({','.join(map(str, concept_ids))})")
            
        # genderCS
        if criteria.gender_cs and criteria.gender_cs.codeset_id:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.gender_cs.codeset_id, "P.gender_concept_id"))
             
        return where_clauses
