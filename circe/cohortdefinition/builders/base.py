"""
Base SQL builder for criteria.

This module contains the abstract base class for building SQL queries from criteria,
mirroring the Java CIRCE-BE CriteriaSqlBuilder.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Set, TypeVar, Generic
from abc import ABC, abstractmethod
from ..criteria import Criteria
from .utils import BuilderOptions, CriteriaColumn

T = TypeVar('T', bound=Criteria)


class CriteriaSqlBuilder(ABC, Generic[T]):
    """Abstract base class for building SQL queries from criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.CriteriaSqlBuilder
    """
    
    def get_criteria_sql(self, criteria: T, options: Optional[BuilderOptions] = None) -> str:
        """Get SQL query for criteria.
        
        Java equivalent: CriteriaSqlBuilder.getCriteriaSql(T criteria)
        """
        return self.get_criteria_sql_with_options(criteria, options)
    
    def get_criteria_sql_with_options(self, criteria: T, options: Optional[BuilderOptions]) -> str:
        """Get SQL query for criteria with builder options.
        
        Java equivalent: CriteriaSqlBuilder.getCriteriaSql(T criteria, BuilderOptions options)
        """
        if options is None:
            options = BuilderOptions()
            
        query = self.get_query_template()
        
        query = self.embed_codeset_clause(query, criteria)
        
        select_clauses = self.resolve_select_clauses(criteria, options)
        join_clauses = self.resolve_join_clauses(criteria, options)
        where_clauses = self.resolve_where_clauses(criteria, options)
        
        query = self.embed_ordinal_expression(query, criteria, where_clauses)
        
        query = self.embed_select_clauses(query, select_clauses)
        query = self.embed_join_clauses(query, join_clauses)
        query = self.embed_where_clauses(query, where_clauses)
        
        if options is not None:
            filtered_columns = [
                column for column in options.additional_columns 
                if column not in self.get_default_columns()
            ]
            if filtered_columns:
                query = query.replace("@additionalColumns", ", " + self.get_additional_columns(filtered_columns))
            else:
                query = query.replace("@additionalColumns", "")
        else:
            query = query.replace("@additionalColumns", "")
        
        return query
    
    @abstractmethod
    def get_table_column_for_criteria_column(self, column: CriteriaColumn) -> str:
        """Get table column name for criteria column.
        
        Java equivalent: CriteriaSqlBuilder.getTableColumnForCriteriaColumn(CriteriaColumn column)
        """
        pass
    
    @abstractmethod
    def get_query_template(self) -> str:
        """Get the SQL query template.
        
        Java equivalent: CriteriaSqlBuilder.getQueryTemplate()
        """
        pass
    
    @abstractmethod
    def get_default_columns(self) -> Set[CriteriaColumn]:
        """Get default columns for this builder.
        
        Java equivalent: CriteriaSqlBuilder.getDefaultColumns()
        """
        pass
    
    def embed_codeset_clause(self, query: str, criteria: T) -> str:
        """Embed codeset clause in query.
        
        Java equivalent: CriteriaSqlBuilder.embedCodesetClause()
        """
        # This would need to be implemented based on the Java logic
        return query.replace("@codesetClause", "")
    
    def resolve_select_clauses(self, criteria: T, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve select clauses for criteria.
        
        Java equivalent: CriteriaSqlBuilder.resolveSelectClauses()
        """
        # This would need to be implemented based on the Java logic
        return []
    
    def resolve_join_clauses(self, criteria: T, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve join clauses for criteria.
        
        Java equivalent: CriteriaSqlBuilder.resolveJoinClauses()
        """
        # This would need to be implemented based on the Java logic
        return []
    
    def resolve_where_clauses(self, criteria: T, options: Optional[BuilderOptions] = None) -> List[str]:
        """Resolve where clauses for criteria.
        
        Java equivalent: CriteriaSqlBuilder.resolveWhereClauses()
        """
        # This would need to be implemented based on the Java logic
        return []
    
    def embed_ordinal_expression(self, query: str, criteria: T, where_clauses: List[str]) -> str:
        """Embed ordinal expression in query.
        
        Java equivalent: CriteriaSqlBuilder.embedOrdinalExpression()
        """
        # This would need to be implemented based on the Java logic
        return query.replace("@ordinalExpression", "")
    
    def embed_select_clauses(self, query: str, select_clauses: List[str]) -> str:
        """Embed select clauses in query.
        
        Java equivalent: CriteriaSqlBuilder.embedSelectClauses()
        Note: Reference uses no space after comma
        """
        select_clause = ",".join(select_clauses) if select_clauses else ""
        return query.replace("@selectClause", select_clause)
    
    def embed_join_clauses(self, query: str, join_clauses: List[str]) -> str:
        """Embed join clauses in query.
        
        Java equivalent: CriteriaSqlBuilder.embedJoinClauses()
        """
        join_clause = " ".join(join_clauses) if join_clauses else ""
        return query.replace("@joinClause", join_clause)
    
    def embed_where_clauses(self, query: str, where_clauses: List[str]) -> str:
        """Embed where clauses in query.
        
        Java equivalent: CriteriaSqlBuilder.embedWhereClauses()
        """
        where_clause = ""
        if where_clauses:
            where_clause = "WHERE " + " AND ".join(where_clauses)
        return query.replace("@whereClause", where_clause)
    
    def get_additional_columns(self, columns: List[CriteriaColumn]) -> str:
        """Get additional columns string.
        
        Java equivalent: CriteriaSqlBuilder.getAdditionalColumns()
        """
        return ", ".join([f"{self.get_table_column_for_criteria_column(col)} as {col.value}" for col in columns])
