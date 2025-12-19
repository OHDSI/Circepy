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
# Note: Uses lowercase select/from to match Java output
PROCEDURE_OCCURRENCE_TEMPLATE = """-- Begin Procedure Occurrence Criteria
select C.person_id, C.procedure_occurrence_id as event_id, C.start_date, C.end_date,
       C.visit_occurrence_id, C.start_date as sort_date@additionalColumns
from 
(
  select @selectClause @ordinalExpression
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
    DEFAULT_SELECT_COLUMNS = [
        "po.person_id",
        "po.procedure_occurrence_id",
        "po.procedure_concept_id",
        "po.visit_occurrence_id",
        "po.quantity",
        "po.procedure_date as start_date",
        " DATEADD(day,1,po.procedure_date) as end_date"
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
        codeset_clause = ""
        if hasattr(criteria, 'codeset_id') and criteria.codeset_id is not None:
            codeset_clause = f"JOIN #Codesets cs on (po.procedure_concept_id = cs.concept_id and cs.codeset_id = {criteria.codeset_id})"
        return query.replace("@codesetClause", codeset_clause)
    
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
