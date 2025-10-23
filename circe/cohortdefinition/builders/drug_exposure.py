"""
Drug Exposure SQL Builder.

This module contains the SQL builder for drug exposure criteria,
mirroring the Java CIRCE-BE DrugExposureSqlBuilder.
"""

from typing import List, Optional, Set
from ..criteria import Criteria
from .base import CriteriaSqlBuilder
from .utils import BuilderOptions, CriteriaColumn

# SQL template - equivalent to Java ResourceHelper.GetResourceAsString
DRUG_EXPOSURE_TEMPLATE = """-- Begin Drug Exposure Criteria
SELECT C.person_id, C.drug_exposure_id as event_id, C.drug_exposure_start_date, C.drug_exposure_end_date,
  C.visit_occurrence_id, C.drug_exposure_start_date as sort_date@additionalColumns
FROM 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.DRUG_EXPOSURE de
  @codesetClause
) C
@joinClause
@whereClause
-- End Drug Exposure Criteria"""


class DrugExposureSqlBuilder(CriteriaSqlBuilder[Criteria]):
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
        "de.visit_occurrence_id"
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
            return "(DATEDIFF(d,C.drug_exposure_start_date, C.drug_exposure_end_date))"
        elif column == CriteriaColumn.START_DATE:
            return "C.drug_exposure_start_date"
        elif column == CriteriaColumn.END_DATE:
            return "C.drug_exposure_end_date"
        elif column == CriteriaColumn.VISIT_ID:
            return "C.visit_occurrence_id"
        else:
            return f"C.{column.value}"
    
    def embed_codeset_clause(self, query: str, criteria: Criteria) -> str:
        """Embed codeset clause in query.
        
        Java equivalent: DrugExposureSqlBuilder.embedCodesetClause()
        """
        # This would need to be implemented based on the Java logic
        # For now, return empty codeset clause
        return query.replace("@codesetClause", "")
    
    def resolve_select_clauses(self, criteria: Criteria) -> List[str]:
        """Resolve select clauses for criteria.
        
        Java equivalent: DrugExposureSqlBuilder.resolveSelectClauses()
        """
        # This would need to be implemented based on the Java logic
        # For now, return default select columns
        return self.DEFAULT_SELECT_COLUMNS.copy()
    
    def resolve_join_clauses(self, criteria: Criteria) -> List[str]:
        """Resolve join clauses for criteria.
        
        Java equivalent: DrugExposureSqlBuilder.resolveJoinClauses()
        """
        # This would need to be implemented based on the Java logic
        return []
    
    def resolve_where_clauses(self, criteria: Criteria) -> List[str]:
        """Resolve where clauses for criteria.
        
        Java equivalent: DrugExposureSqlBuilder.resolveWhereClauses()
        """
        # This would need to be implemented based on the Java logic
        return []
