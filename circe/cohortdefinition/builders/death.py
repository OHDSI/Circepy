"""
Death SQL Builder

This module contains the SQL builder for Death criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Set, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import CriteriaSqlBuilder
from .utils import CriteriaColumn, BuilderOptions, BuilderUtils
from ..criteria import Death


class DeathSqlBuilder(CriteriaSqlBuilder[Death]):
    """SQL builder for Death criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.DeathSqlBuilder
    """
    
    def get_query_template(self) -> str:
        """Get the SQL query template for death criteria."""
        return """-- Begin Death Criteria
SELECT C.person_id, C.death_date as start_date, C.death_date as end_date,
       C.cause_concept_id as domain_concept@additionalColumns
FROM 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.DEATH d
  @codesetClause
) C
@joinClause
WHERE @whereClause
-- End Death Criteria
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for death criteria."""
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID
        }
    
    def get_table_column_for_criteria_column(self, criteria_column: CriteriaColumn) -> str:
        """Get table column for criteria column."""
        column_mapping = {
            CriteriaColumn.DOMAIN_CONCEPT: "coalesce(C.cause_concept_id,0)",
            CriteriaColumn.DURATION: "CAST(1 as int)"
        }
        return column_mapping.get(criteria_column, "NULL")
    
    
    def embed_codeset_clause(self, query: str, criteria: Death) -> str:
        """Embed codeset clause for death criteria."""
        return query.replace("@codesetClause", BuilderUtils.get_codeset_join_expression(
            criteria.codeset_id, 
            "d.cause_concept_id",
            criteria.death_source_concept,
            "d.cause_source_concept_id"
        ))
    
    def embed_ordinal_expression(self, query: str, criteria: Death, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query.
        
        Java DeathSqlBuilder overrides this to return query as is (does nothing).
        """
        return query

    def resolve_select_clauses(self, criteria: Death, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for death criteria."""
        select_cols = [
            "d.person_id",
            "d.cause_concept_id"
        ]
        
        # deathType
        if (criteria.death_type and len(criteria.death_type) > 0) or \
           (criteria.death_type_cs and criteria.death_type_cs.codeset_id):
            select_cols.append("d.death_type_concept_id")
            
        # dateAdjustment or default start/end dates
        if criteria.date_adjustment:
             select_cols.append(BuilderUtils.get_date_adjustment_expression(
                criteria.date_adjustment, "d.death_date", "DATEADD(day,1,d.death_date)"
             ))
        else:
             select_cols.append("d.death_date, DATEADD(day,1,d.death_date) as end_date")
             
        return select_cols
    
    def resolve_join_clauses(self, criteria: Death, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for death criteria."""
        joins = []
        
        # join to PERSON
        if criteria.age or \
           (criteria.gender and len(criteria.gender) > 0) or \
           (criteria.gender_cs and criteria.gender_cs.codeset_id):
            joins.append("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id")
            
        return joins
    
    def resolve_where_clauses(self, criteria: Death, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for death criteria."""
        # Note: Java DeathSqlBuilder calls super.resolveWhereClauses(criteria)
        # But super.resolveWhereClauses handles generic logic like codeset_id check if we used standard logic?
        # Actually CriteriaSqlBuilder.resolveWhereClauses does:
        # if (criteria.codesetId != null) ...
        # But DeathSqlBuilder implementation in Java overrides embedCodesetClause to use JOIN.
        # Let's verify base class behavior. 
        # Java CriteriaSqlBuilder checks codesetId and adds "C.primary_concept_id in ... " if codesetId is present.
        # BUT specific builders often override embedCodesetClause to use JOIN #Codesets.
        # If embedCodesetClause uses JOIN, then we usually DON'T want WHERE clause filter on codesetId?
        # Java implementation calls super.resolveWhereClauses(criteria).
        # Let's assume we need to call super.
        
        where_clauses = super().resolve_where_clauses(criteria)
        
        # occurrenceStartDate
        if criteria.occurrence_start_date:
            date_clause = BuilderUtils.build_date_range_clause(
                criteria.occurrence_start_date, "C.start_date"
            )
            if date_clause:
                where_clauses.append(date_clause)
        
        # deathType
        if criteria.death_type and len(criteria.death_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.death_type)
            op = "not in" if criteria.death_type_exclude else "in"
            where_clauses.append(f"C.death_type_concept_id {op} ({','.join(map(str, concept_ids))})")
            
        # deathTypeCS
        if criteria.death_type_cs and criteria.death_type_cs.codeset_id:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.death_type_cs.codeset_id, "C.death_type_concept_id"))

        # age
        if criteria.age:
            where_clauses.append(BuilderUtils.build_numeric_range_clause(
                criteria.age, "YEAR(C.start_date) - P.year_of_birth"
            ))
            
        # gender
        if criteria.gender and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            where_clauses.append(f"P.gender_concept_id in ({','.join(map(str, concept_ids))})")
            
        # genderCS
        if criteria.gender_cs and criteria.gender_cs.codeset_id:
             where_clauses.append(BuilderUtils.get_codeset_in_expression(criteria.gender_cs.codeset_id, "P.gender_concept_id"))
             
        return where_clauses
