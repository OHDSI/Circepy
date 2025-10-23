"""
Condition Occurrence SQL Builder.

This module contains the SQL builder for condition occurrence criteria,
mirroring the Java CIRCE-BE ConditionOccurrenceSqlBuilder.
"""

from typing import List, Optional, Set
from ..criteria import Criteria
from .base import CriteriaSqlBuilder
from .utils import BuilderOptions, CriteriaColumn

# SQL template - equivalent to Java ResourceHelper.GetResourceAsString
CONDITION_OCCURRENCE_TEMPLATE = """-- Begin Condition Occurrence Criteria
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
-- End Condition Occurrence Criteria"""


class ConditionOccurrenceSqlBuilder(CriteriaSqlBuilder[Criteria]):
    """SQL builder for condition occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.ConditionOccurrenceSqlBuilder
    """
    
    # Default columns are those that are specified in the template
    DEFAULT_COLUMNS = {
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.VISIT_ID
    }
    
    # Default select columns are the columns that will always be returned from the subquery
    DEFAULT_SELECT_COLUMNS = [
        "co.person_id",
        "co.condition_occurrence_id",
        "co.condition_concept_id",
        "co.visit_occurrence_id"
    ]
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for this builder.
        
        Java equivalent: ConditionOccurrenceSqlBuilder.getDefaultColumns()
        """
        return self.DEFAULT_COLUMNS
    
    def get_query_template(self) -> str:
        """Get the SQL query template.
        
        Java equivalent: ConditionOccurrenceSqlBuilder.getQueryTemplate()
        """
        return CONDITION_OCCURRENCE_TEMPLATE
    
    def get_table_column_for_criteria_column(self, column: CriteriaColumn) -> str:
        """Get table column name for criteria column.
        
        Java equivalent: ConditionOccurrenceSqlBuilder.getTableColumnForCriteriaColumn()
        """
        if column == CriteriaColumn.DOMAIN_CONCEPT:
            return "C.condition_concept_id"
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
    
    def embed_codeset_clause(self, query: str, criteria: Criteria) -> str:
        """Embed codeset clause in query.
        
        Java equivalent: ConditionOccurrenceSqlBuilder.embedCodesetClause()
        """
        # This would need to be implemented based on the Java logic
        # For now, return empty codeset clause
        return query.replace("@codesetClause", "")
    
    def resolve_select_clauses(self, criteria: Criteria) -> List[str]:
        """Resolve select clauses for criteria.
        
        Java equivalent: ConditionOccurrenceSqlBuilder.resolveSelectClauses()
        """
        # This would need to be implemented based on the Java logic
        # For now, return default select columns
        return self.DEFAULT_SELECT_COLUMNS.copy()
    
    def resolve_join_clauses(self, criteria: Criteria) -> List[str]:
        """Resolve join clauses for criteria.
        
        Java equivalent: ConditionOccurrenceSqlBuilder.resolveJoinClauses()
        """
        # This would need to be implemented based on the Java logic
        return []
    
    def resolve_where_clauses(self, criteria: Criteria) -> List[str]:
        """Resolve where clauses for criteria.
        
        Java equivalent: ConditionOccurrenceSqlBuilder.resolveWhereClauses()
        """
        # This would need to be implemented based on the Java logic
        return []
