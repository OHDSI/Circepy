"""
Drug Exposure SQL Builder.

This module contains the SQL builder for drug exposure criteria,
mirroring the Java CIRCE-BE DrugExposureSqlBuilder.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Set
from ..criteria import DrugExposure
from .base import CriteriaSqlBuilder
from .utils import BuilderOptions, CriteriaColumn, BuilderUtils

# SQL template - equivalent to Java ResourceHelper.GetResourceAsString
DRUG_EXPOSURE_TEMPLATE = """-- Begin Drug Exposure Criteria
SELECT C.person_id, C.drug_exposure_id as event_id, C.start_date, C.end_date,
       C.visit_occurrence_id, C.start_date as sort_date@additionalColumns
FROM 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.DRUG_EXPOSURE de
@codesetClause
) C
@joinClause
@whereClause
-- End Drug Exposure Criteria
"""


class DrugExposureSqlBuilder(CriteriaSqlBuilder[DrugExposure]):
    """SQL builder for drug exposure criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.DrugExposureSqlBuilder
    """
    
    # Default columns are those that are specified in the template
    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.VISIT_ID
    }
    
    # Default select columns are the columns that will always be returned from the subquery
    DEFAULT_SELECT_COLUMNS = [
        "de.person_id",
        "de.drug_exposure_id",
        "de.drug_concept_id",
        "de.visit_occurrence_id",
        "days_supply",
        "quantity",
        "refills"
    ]
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for this builder.
        
        Java equivalent: DrugExposureSqlBuilder.getDefaultColumns()
        """
        return self.DEFAULT_COLUMNS
    
    def get_query_template(self) -> str:
        """Get the SQL query template.
        
        Java equivalent: DrugExposureSqlBuilder.getQueryTemplate()
        """
        return DRUG_EXPOSURE_TEMPLATE
    
    def get_table_column_for_criteria_column(self, column: CriteriaColumn) -> str:
        """Get table column name for criteria column.
        
        Java equivalent: DrugExposureSqlBuilder.getTableColumnForCriteriaColumn()
        """
        if column == CriteriaColumn.DOMAIN_CONCEPT:
            return "C.drug_concept_id"
        elif column == CriteriaColumn.DURATION:
            return "(DATEDIFF(d,C.start_date, C.end_date))"
        elif column == CriteriaColumn.START_DATE:
            return "C.start_date"
        elif column == CriteriaColumn.END_DATE:
            return "C.end_date"
        elif column == CriteriaColumn.VISIT_ID:
            return "C.visit_occurrence_id"
        else:
            return f"C.{column.value}"
    
    def embed_codeset_clause(self, query: str, criteria: DrugExposure) -> str:
        """Embed codeset clause in query.
        
        Java equivalent: DrugExposureSqlBuilder.embedCodesetClause()
        """
        return query.replace("@codesetClause",
                           BuilderUtils.get_codeset_join_expression(
                               criteria.codeset_id,
                               "de.drug_concept_id",
                               criteria.drug_source_concept,
                               "de.drug_source_concept_id"
                           ))
    
    def embed_ordinal_expression(self, query: str, criteria: DrugExposure, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query.
        
        Java equivalent: DrugExposureSqlBuilder.embedOrdinalExpression()
        """
        # first
        if criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace("@ordinalExpression", ", row_number() over (PARTITION BY de.person_id ORDER BY de.drug_exposure_start_date, de.drug_exposure_id) as ordinal")
        else:
            query = query.replace("@ordinalExpression", "")
        
        return query

    def resolve_select_clauses(self, criteria: DrugExposure, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for drug exposure criteria.
        
        Java equivalent: DrugExposureSqlBuilder.resolveSelectClauses()
        """
        # Default select columns that are always returned from inner subquery
        select_cols = [
            "de.person_id",
            "de.drug_exposure_id", 
            "de.drug_concept_id",
            "de.visit_occurrence_id",
            "days_supply",
            "quantity",
            "refills"
        ]

        
        # drugType
        if (criteria.drug_type and len(criteria.drug_type) > 0) or criteria.drug_type_cs:
            select_cols.append("de.drug_type_concept_id")
            
        # stopReason
        if criteria.stop_reason:
            select_cols.append("de.stop_reason")

        # routeConcept
        if (criteria.route_concept and len(criteria.route_concept) > 0) or criteria.route_concept_cs:
            select_cols.append("de.route_concept_id")

        # providerSpecialty
        if (criteria.provider_specialty and len(criteria.provider_specialty) > 0) or criteria.provider_specialty_cs:
            select_cols.append("de.provider_id")

        # doseUnit
        if (criteria.dose_unit and len(criteria.dose_unit) > 0) or criteria.dose_unit_cs:
            select_cols.append("de.dose_unit_concept_id")

        # LotNumber
        if criteria.lot_number:
            select_cols.append("de.lot_number")
        
        # dateAdjustment or default start/end dates
        if criteria.date_adjustment:
            select_cols.append(BuilderUtils.get_date_adjustment_expression(
                criteria.date_adjustment,
                "de.drug_exposure_start_date" if criteria.date_adjustment.start_with == "start_date" else "de.drug_exposure_end_date",
                "de.drug_exposure_start_date" if criteria.date_adjustment.end_with == "start_date" else "de.drug_exposure_end_date"
            ))
        else:
            select_cols.append("de.drug_exposure_start_date as start_date, COALESCE(de.drug_exposure_end_date, DATEADD(day,de.days_supply,de.drug_exposure_start_date), DATEADD(day,1,de.drug_exposure_start_date)) as end_date")
        
        return select_cols

    
    def resolve_join_clauses(self, criteria: DrugExposure, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for drug exposure criteria.
        
        Java equivalent: DrugExposureSqlBuilder.resolveJoinClauses()
        """
        join_clauses = []
        
        # Join to PERSON if age or gender conditions are present
        if criteria.age or (criteria.gender and len(criteria.gender) > 0) or criteria.gender_cs:
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
        
        # Join to VISIT_OCCURRENCE
        if (criteria.visit_type and len(criteria.visit_type) > 0) or criteria.visit_type_cs:
            join_clauses.append("JOIN @cdm_database_schema.VISIT_OCCURRENCE V on C.visit_occurrence_id = V.visit_occurrence_id and C.person_id = V.person_id")

        # Join to PROVIDER if provider specialty conditions are present
        if (criteria.provider_specialty and len(criteria.provider_specialty) > 0) or criteria.provider_specialty_cs:
            join_clauses.append("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id")
        
        return join_clauses
    
    def resolve_where_clauses(self, criteria: DrugExposure, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for drug exposure criteria.
        
        Java equivalent: DrugExposureSqlBuilder.resolveWhereClauses()
        """
        where_clauses = super().resolve_where_clauses(criteria)
        
        # Note: codeset filtering is now handled via JOIN in inner query, not WHERE clause
        
        # Add occurrence dates
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
        
        # drugType
        if criteria.drug_type and len(criteria.drug_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.drug_type)
            operator = "not in" if criteria.drug_type_exclude else "in"
            where_clauses.append(f"C.drug_type_concept_id {operator} ({','.join(map(str, concept_ids))})")
            
        # drugTypeCS
        if criteria.drug_type_cs:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.drug_type_cs.codeset_id, "C.drug_type_concept_id"))

        # stopReason
        if criteria.stop_reason:
            where_clauses.append(BuilderUtils.build_text_filter_clause(criteria.stop_reason, "C.stop_reason"))

        # routeConcept
        if criteria.route_concept and len(criteria.route_concept) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.route_concept)
            where_clauses.append(f"C.route_concept_id in ({','.join(map(str, concept_ids))})")
            
        # routeConceptCS
        if criteria.route_concept_cs:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.route_concept_cs.codeset_id, "C.route_concept_id"))

        # doseUnit
        if criteria.dose_unit and len(criteria.dose_unit) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.dose_unit)
            where_clauses.append(f"C.dose_unit_concept_id in ({','.join(map(str, concept_ids))})")

        # doseUnitCS
        if criteria.dose_unit_cs:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.dose_unit_cs.codeset_id, "C.dose_unit_concept_id"))

        # LotNumber
        if criteria.lot_number:
            where_clauses.append(BuilderUtils.build_text_filter_clause(criteria.lot_number, "C.lot_number"))

        # refills
        if criteria.refills:
            where_clauses.append(BuilderUtils.build_numeric_range_clause("C.refills", criteria.refills))

        # quantity
        if criteria.quantity:
            where_clauses.append(BuilderUtils.build_numeric_range_clause("C.quantity", criteria.quantity))

        # daysSupply
        if criteria.days_supply:
            where_clauses.append(BuilderUtils.build_numeric_range_clause("C.days_supply", criteria.days_supply))

        # age
        if criteria.age:
            where_clauses.append(BuilderUtils.build_numeric_range_clause("YEAR(C.start_date) - P.year_of_birth", criteria.age))
            
        # gender
        if criteria.gender and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            where_clauses.append(f"P.gender_concept_id in ({','.join(map(str, concept_ids))})")

        # genderCS
        if criteria.gender_cs:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.gender_cs.codeset_id, "P.gender_concept_id"))
        
        # providerSpecialty
        if criteria.provider_specialty and len(criteria.provider_specialty) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.provider_specialty)
            where_clauses.append(f"PR.specialty_concept_id in ({','.join(map(str, concept_ids))})")

        # providerSpecialtyCS
        if criteria.provider_specialty_cs:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.provider_specialty_cs.codeset_id, "PR.specialty_concept_id"))

        # visitType
        if criteria.visit_type and len(criteria.visit_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.visit_type)
            where_clauses.append(f"V.visit_concept_id in ({','.join(map(str, concept_ids))})")
            
        # visitTypeCS
        if criteria.visit_type_cs:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.visit_type_cs.codeset_id, "V.visit_concept_id"))
        
        return [c for c in where_clauses if c]  # Filter out None values
