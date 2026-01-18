"""
Procedure Occurrence SQL Builder.

This module contains the SQL builder for procedure occurrence criteria,
mirroring the Java CIRCE-BE ProcedureOccurrenceSqlBuilder.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Set
from ..criteria import Criteria
from .base import CriteriaSqlBuilder
from .utils import BuilderOptions, CriteriaColumn, BuilderUtils

# SQL template - equivalent to Java ResourceHelper.GetResourceAsString
# Note: Uses lowercase select/from to match Java output
PROCEDURE_OCCURRENCE_TEMPLATE = """-- Begin Procedure Occurrence Criteria
SELECT C.person_id, C.procedure_occurrence_id as event_id, C.start_date, C.end_date,
       C.visit_occurrence_id, C.start_date as sort_date@additionalColumns
FROM 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.PROCEDURE_OCCURRENCE po
@codesetClause
) C
@joinClause
@whereClause
-- End Procedure Occurrence Criteria
"""


class ProcedureOccurrenceSqlBuilder(CriteriaSqlBuilder[Criteria]):
    """SQL builder for procedure occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.ProcedureOccurrenceSqlBuilder
    """
    
    # Default columns are those that are specified in the template
    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.VISIT_ID
    }
    
    # Default select columns are the columns that will always be returned from the subquery
    # Note: Matches Java output format exactly - ending with space on last item
    # DATE columns removed from defaults to be handled dynamically like in Java
    DEFAULT_SELECT_COLUMNS = [
        "po.person_id",
        "po.procedure_occurrence_id",
        "po.procedure_concept_id",
        "po.visit_occurrence_id",
        "po.quantity"
    ]
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for this builder.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.getDefaultColumns()
        """
        return self.DEFAULT_COLUMNS
    
    def get_query_template(self) -> str:
        """Get the SQL query template.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.getQueryTemplate()
        """
        return PROCEDURE_OCCURRENCE_TEMPLATE
    
    def get_table_column_for_criteria_column(self, column: CriteriaColumn) -> str:
        """Get table column name for criteria column.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.getTableColumnForCriteriaColumn()
        """
        if column == CriteriaColumn.DOMAIN_CONCEPT:
            return "C.procedure_concept_id"
        elif column == CriteriaColumn.DURATION:
            return "CAST(1 as int)"
        elif column == CriteriaColumn.QUANTITY:
            return "C.quantity"
        elif column == CriteriaColumn.START_DATE:
            return "C.start_date"
        elif column == CriteriaColumn.END_DATE:
            return "C.end_date"
        elif column == CriteriaColumn.VISIT_ID:
            return "C.visit_occurrence_id"
        else:
            return f"C.{column.value}"
    

    def embed_ordinal_expression(self, query: str, criteria: Criteria, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.embedOrdinalExpression()
        """
        # first
        if hasattr(criteria, 'first') and criteria.first:
            where_clauses.append("C.ordinal = 1")
            query = query.replace("@ordinalExpression", ", row_number() over (PARTITION BY po.person_id ORDER BY po.procedure_date, po.procedure_occurrence_id) as ordinal")
        else:
            query = query.replace("@ordinalExpression", "")
        
        return query
    
    def embed_codeset_clause(self, query: str, criteria: Criteria) -> str:
        """Embed codeset clause in query.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.embedCodesetClause()
        """
        return query.replace("@codesetClause",
                           BuilderUtils.get_codeset_join_expression(
                               criteria.codeset_id if hasattr(criteria, 'codeset_id') else None,
                               "po.procedure_concept_id",
                               criteria.procedure_source_concept if hasattr(criteria, 'procedure_source_concept') else None,
                               "po.procedure_source_concept_id"
                           ))
    
    def resolve_select_clauses(self, criteria: Criteria, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for criteria.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.resolveSelectClauses()
        """
        select_cols = list(self.DEFAULT_SELECT_COLUMNS)
        
        # procedureType
        if (hasattr(criteria, 'procedure_type') and criteria.procedure_type and len(criteria.procedure_type) > 0) or \
           (hasattr(criteria, 'procedure_type_cs') and criteria.procedure_type_cs is not None):
            select_cols.append("po.procedure_type_concept_id")

        # modifier
        if (hasattr(criteria, 'modifier') and criteria.modifier and len(criteria.modifier) > 0) or \
           (hasattr(criteria, 'modifier_cs') and criteria.modifier_cs is not None):
            select_cols.append("po.modifier_concept_id")
            
        # providerSpecialty
        if (hasattr(criteria, 'provider_specialty') and criteria.provider_specialty and len(criteria.provider_specialty) > 0) or \
           (hasattr(criteria, 'provider_specialty_cs') and criteria.provider_specialty_cs is not None):
            select_cols.append("po.provider_id")

        # dateAdjustment or default start/end dates
        if hasattr(criteria, 'date_adjustment') and criteria.date_adjustment:
            select_cols.append(BuilderUtils.get_date_adjustment_expression(
                criteria.date_adjustment,
                "po.procedure_date" if criteria.date_adjustment.start_with == "start_date" else "DATEADD(day,1,po.procedure_date)",
                "po.procedure_date" if criteria.date_adjustment.end_with == "start_date" else "DATEADD(day,1,po.procedure_date)"
            ))
        else:
            select_cols.append("po.procedure_date as start_date, DATEADD(day,1,po.procedure_date) as end_date")
            
        return select_cols
    
    def resolve_join_clauses(self, criteria: Criteria, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for criteria.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.resolveJoinClauses()
        """
        join_clauses = []
        
        # join to PERSON
        if (hasattr(criteria, 'age') and criteria.age) or \
           (hasattr(criteria, 'gender') and criteria.gender and len(criteria.gender) > 0) or \
           (hasattr(criteria, 'gender_cs') and criteria.gender_cs is not None):
            join_clauses.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
            
        # visitType
        if (hasattr(criteria, 'visit_type') and criteria.visit_type and len(criteria.visit_type) > 0) or \
           (hasattr(criteria, 'visit_type_cs') and criteria.visit_type_cs is not None):
            join_clauses.append("JOIN @cdm_database_schema.VISIT_OCCURRENCE V on C.visit_occurrence_id = V.visit_occurrence_id and C.person_id = V.person_id")
            
        # providerSpecialty
        if (hasattr(criteria, 'provider_specialty') and criteria.provider_specialty and len(criteria.provider_specialty) > 0) or \
           (hasattr(criteria, 'provider_specialty_cs') and criteria.provider_specialty_cs is not None):
            join_clauses.append("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id")
            
        return join_clauses
    
    def resolve_where_clauses(self, criteria: Criteria, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for criteria.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.resolveWhereClauses()
        """
        where_clauses = list(super().resolve_where_clauses(criteria, options))
        
        # occurrenceStartDate
        if hasattr(criteria, 'occurrence_start_date') and criteria.occurrence_start_date:
            where_clauses.append(BuilderUtils.build_date_range_clause("C.start_date", criteria.occurrence_start_date))

        # procedureType
        if hasattr(criteria, 'procedure_type') and criteria.procedure_type and len(criteria.procedure_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.procedure_type)
            exclude = "not " if hasattr(criteria, 'procedure_type_exclude') and criteria.procedure_type_exclude else ""
            where_clauses.append(f"C.procedure_type_concept_id {exclude}in ({','.join(map(str, concept_ids))})")
            
        # procedureTypeCS
        if hasattr(criteria, 'procedure_type_cs') and criteria.procedure_type_cs is not None:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.procedure_type_cs.codeset_id, "C.procedure_type_concept_id"))

        # modifier
        if hasattr(criteria, 'modifier') and criteria.modifier and len(criteria.modifier) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.modifier)
            where_clauses.append(f"C.modifier_concept_id in ({','.join(map(str, concept_ids))})")
                
        # modifierCS
        if hasattr(criteria, 'modifier_cs') and criteria.modifier_cs is not None:
            where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.modifier_cs.codeset_id, "C.modifier_concept_id"))
        
        # quantity
        if hasattr(criteria, 'quantity') and criteria.quantity:
             where_clauses.append(BuilderUtils.build_numeric_range_clause("C.quantity", criteria.quantity))
            
        # age
        if hasattr(criteria, 'age') and criteria.age:
             where_clauses.append(BuilderUtils.build_numeric_range_clause("YEAR(C.start_date) - P.year_of_birth", criteria.age))

        # gender
        if hasattr(criteria, 'gender') and criteria.gender and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            where_clauses.append(f"P.gender_concept_id in ({','.join(map(str, concept_ids))})")

        # genderCS
        if hasattr(criteria, 'gender_cs') and criteria.gender_cs is not None:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.gender_cs.codeset_id, "P.gender_concept_id"))
             
        # providerSpecialty
        if hasattr(criteria, 'provider_specialty') and criteria.provider_specialty and len(criteria.provider_specialty) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.provider_specialty)
            where_clauses.append(f"PR.specialty_concept_id in ({','.join(map(str, concept_ids))})")
            
        # providerSpecialtyCS
        if hasattr(criteria, 'provider_specialty_cs') and criteria.provider_specialty_cs is not None:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.provider_specialty_cs.codeset_id, "PR.specialty_concept_id"))

        # visitType
        if hasattr(criteria, 'visit_type') and criteria.visit_type and len(criteria.visit_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.visit_type)
            where_clauses.append(f"V.visit_concept_id in ({','.join(map(str, concept_ids))})")
            
        # visitTypeCS
        if hasattr(criteria, 'visit_type_cs') and criteria.visit_type_cs is not None:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.visit_type_cs.codeset_id, "V.visit_concept_id"))

        return where_clauses
