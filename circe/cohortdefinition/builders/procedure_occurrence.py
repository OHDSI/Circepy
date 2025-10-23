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
from .utils import BuilderOptions, CriteriaColumn

# SQL template - equivalent to Java ResourceHelper.GetResourceAsString
PROCEDURE_OCCURRENCE_TEMPLATE = """-- Begin Procedure Occurrence Criteria
SELECT C.person_id, C.procedure_occurrence_id as event_id, C.procedure_date, C.procedure_date,
  C.visit_occurrence_id, C.procedure_date as sort_date@additionalColumns
FROM 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.PROCEDURE_OCCURRENCE po
  @codesetClause
) C
@joinClause
@whereClause
-- End Procedure Occurrence Criteria"""


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
    DEFAULT_SELECT_COLUMNS = [
        "po.person_id",
        "po.procedure_occurrence_id",
        "po.procedure_concept_id",
        "po.visit_occurrence_id"
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
            return "0"  # Procedures typically don't have duration
        elif column == CriteriaColumn.START_DATE:
            return "C.procedure_date"
        elif column == CriteriaColumn.END_DATE:
            return "C.procedure_date"  # Same as start date for procedures
        elif column == CriteriaColumn.VISIT_ID:
            return "C.visit_occurrence_id"
        else:
            return f"C.{column.value}"
    
    def embed_codeset_clause(self, query: str, criteria: Criteria) -> str:
        """Embed codeset clause in query.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.embedCodesetClause()
        """
        # This would need to be implemented based on the Java logic
        # For now, return empty codeset clause
        return query.replace("@codesetClause", "")
    
    def resolve_select_clauses(self, criteria: Criteria, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for criteria.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.resolveSelectClauses()
        """
        # This would need to be implemented based on the Java logic
        # For now, return default select columns
        return self.DEFAULT_SELECT_COLUMNS.copy()
    
    def resolve_join_clauses(self, criteria: Criteria, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for criteria.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.resolveJoinClauses()
        """
        # This would need to be implemented based on the Java logic
        return []
    
    def resolve_where_clauses(self, criteria: Criteria, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for criteria.
        
        Java equivalent: ProcedureOccurrenceSqlBuilder.resolveWhereClauses()
        """
        # This would need to be implemented based on the Java logic
        return []
