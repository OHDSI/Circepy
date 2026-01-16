"""
Dose Era SQL Builder

This module contains the SQL builder for Dose Era criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import DoseEra


class DoseEraSqlBuilder(CriteriaSqlBuilder[DoseEra]):
    """SQL builder for Dose Era criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.DoseEraSqlBuilder
    """
    
    # Default columns are those that are specified in the template, and don't need to be added if specified in 'additionalColumns'
    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.VISIT_ID
    }
    
    # Default select columns are the columns that will always be returned from the subquery, but are added to based on the specific criteria
    DEFAULT_SELECT_COLUMNS = [
        "de.person_id",
        "de.dose_era_id", 
        "de.drug_concept_id",
        "de.unit_concept_id",
        "de.dose_value"
    ]
    
    def get_query_template(self) -> str:
        """Get the SQL query template for dose era criteria."""
        return """-- Begin Dose Era Criteria
SELECT C.person_id, C.dose_era_id as event_id, C.start_date, C.end_date,
    CAST(NULL as bigint) as visit_occurrence_id, C.start_date as sort_date@additionalColumns
FROM 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.DOSE_ERA de
@codesetClause
) C
@joinClause
@whereClause
-- End Dose Era Criteria
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for dose era criteria."""
        return self.DEFAULT_COLUMNS
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DOMAIN_CONCEPT: "C.drug_concept_id",
            CriteriaColumn.DURATION: "DATEDIFF(d, C.start_date, C.end_date)",
            CriteriaColumn.UNIT: "C.unit_concept_id",
            CriteriaColumn.VALUE_AS_NUMBER: "C.dose_value",
            CriteriaColumn.START_DATE: "C.start_date",
            CriteriaColumn.END_DATE: "C.end_date",
            CriteriaColumn.VISIT_ID: "NULL",
            CriteriaColumn.VISIT_ID: "NULL"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    def embed_codeset_clause(self, query: str, criteria: DoseEra) -> str:
        """Embed codeset clause in query.
        
        Note: Reference uses lowercase 'where' and double space before #Codesets
        """
        codeset_clause = ""
        if criteria.codeset_id is not None:
            codeset_clause = f"where de.drug_concept_id in (SELECT concept_id from  #Codesets where codeset_id = {criteria.codeset_id})"
        return query.replace("@codesetClause", codeset_clause)
    
    def embed_ordinal_expression(self, query: str, criteria: DoseEra, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query."""
        # first
        if criteria.first is not None and criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace("@ordinalExpression", ", row_number() over (PARTITION BY de.person_id ORDER BY de.dose_era_start_date, de.dose_era_id) as ordinal")
        else:
            query = query.replace("@ordinalExpression", "")
        return query
    
    def resolve_select_clauses(self, criteria: DoseEra, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for dose era criteria."""
        select_cols = list(self.DEFAULT_SELECT_COLUMNS)
        
        # dateAdjustment or default start/end dates
        if criteria.date_adjustment is not None:
            start_column = "de.dose_era_start_date" if criteria.date_adjustment.start_with == "start_date" else "de.dose_era_end_date"
            end_column = "de.dose_era_start_date" if criteria.date_adjustment.end_with == "start_date" else "de.dose_era_end_date"
            select_cols.append(BuilderUtils.get_date_adjustment_expression(criteria.date_adjustment, start_column, end_column))
        else:
            select_cols.append("de.dose_era_start_date as start_date, de.dose_era_end_date as end_date")
        
        return select_cols
    
    def resolve_join_clauses(self, criteria: DoseEra, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for dose era criteria."""
        join_clauses = []
        
        # join to PERSON
        if (criteria.age_at_start is not None or 
            criteria.age_at_end is not None or
            (criteria.gender is not None and len(criteria.gender) > 0) or
            criteria.gender_cs is not None):
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: DoseEra, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for dose era criteria."""
        where_clauses = []
        
        # eraStartDate
        if criteria.era_start_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.start_date", criteria.era_start_date)
            if date_clause:
                where_clauses.append(date_clause)
        
        # eraEndDate
        if criteria.era_end_date is not None:
            date_clause = BuilderUtils.build_date_range_clause("C.end_date", criteria.era_end_date)
            if date_clause:
                where_clauses.append(date_clause)
        
        # unit
        if criteria.unit is not None and len(criteria.unit) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.unit)
            if concept_ids:
                where_clauses.append(f"C.unit_concept_id in ({','.join(map(str, concept_ids))})")
        
        # unitCS
        if criteria.unit_cs is not None:
            codeset_clause = BuilderUtils.get_codeset_in_expression(criteria.unit_cs.codeset_id, "C.unit_concept_id", criteria.unit_cs.is_exclusion)
            if codeset_clause:
                where_clauses.append(codeset_clause)
        
        # doseValue
        if criteria.dose_value is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause("C.dose_value", criteria.dose_value, ".4f")
            if numeric_clause:
                where_clauses.append(numeric_clause)
        
        # eraLength
        if criteria.era_length is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause("DATEDIFF(d,C.start_date, C.end_date)", criteria.era_length)
            if numeric_clause:
                where_clauses.append(numeric_clause)
        
        # ageAtStart
        if criteria.age_at_start is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause("YEAR(C.start_date) - P.year_of_birth", criteria.age_at_start)
            if numeric_clause:
                where_clauses.append(numeric_clause)
        
        # ageAtEnd
        if criteria.age_at_end is not None:
            numeric_clause = BuilderUtils.build_numeric_range_clause("YEAR(C.end_date) - P.year_of_birth", criteria.age_at_end)
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
        
        return where_clauses
