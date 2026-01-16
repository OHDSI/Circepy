"""
Builder utilities for SQL query generation.

This module contains utility classes and functions for building SQL queries
from cohort definition criteria, mirroring the Java CIRCE-BE builder utilities.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Set, Dict, Any
from enum import Enum
from abc import ABC, abstractmethod
from ..core import DateRange, DateAdjustment, NumericRange, ConceptSetSelection
from ...vocabulary.concept import Concept
from ..criteria import CriteriaColumn


class BuilderOptions:
    """Builder options for SQL query generation.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.BuilderOptions
    """
    
    def __init__(self):
        self.additional_columns: List[CriteriaColumn] = []


class BuilderUtils:
    """Utility class for SQL query building.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.BuilderUtils
    """
    
    # SQL templates - equivalent to Java constants
    CODESET_JOIN_TEMPLATE = "JOIN #Codesets {} on ({} = {}.concept_id and {}.codeset_id = {})"
    CODESET_IN_TEMPLATE = "{} {} in (select concept_id from #Codesets where codeset_id = {})"
    CODESET_NULL_TEMPLATE = "{} is {} null"
    
    # Date adjustment template - equivalent to Java ResourceHelper.GetResourceAsString
    DATE_ADJUSTMENT_TEMPLATE = "DATEADD(day,{}, {}) as start_date, DATEADD(day,{}, {}) as end_date"
    
    STANDARD_ALIAS = "cs"
    NON_STANDARD_ALIAS = "cns"
    
    @staticmethod
    def get_date_adjustment_expression(date_adjustment: DateAdjustment, start_column: str, end_column: str) -> str:
        """Get date adjustment expression for SQL.
        
        Java equivalent: BuilderUtils.getDateAdjustmentExpression()
        """
        return BuilderUtils.DATE_ADJUSTMENT_TEMPLATE.format(
            date_adjustment.start_offset,
            start_column,
            date_adjustment.end_offset,
            end_column
        )
    
    @staticmethod
    def get_codeset_join_expression(
        standard_codeset_id: Optional[int], 
        standard_concept_column: str,
        source_codeset_id: Optional[int], 
        source_concept_column: str
    ) -> str:
        """Get codeset join expression for SQL.
        
        Java equivalent: BuilderUtils.getCodesetJoinExpression()
        """
        codeset_clauses = []
        
        if standard_codeset_id is not None:
            codeset_clauses.append(
                BuilderUtils.CODESET_JOIN_TEMPLATE.format(
                    BuilderUtils.STANDARD_ALIAS,
                    standard_concept_column,
                    BuilderUtils.STANDARD_ALIAS,
                    BuilderUtils.STANDARD_ALIAS,
                    standard_codeset_id
                )
            )
        
        if source_codeset_id is not None:
            codeset_clauses.append(
                BuilderUtils.CODESET_JOIN_TEMPLATE.format(
                    BuilderUtils.NON_STANDARD_ALIAS,
                    source_concept_column,
                    BuilderUtils.NON_STANDARD_ALIAS,
                    BuilderUtils.NON_STANDARD_ALIAS,
                    source_codeset_id
                )
            )
        
        return " ".join(codeset_clauses)
    
    @staticmethod
    def get_codeset_in_expression(codeset_id: int, column_name: str, is_exclusion: bool = False) -> str:
        """Get codeset IN expression for SQL.
        
        Java equivalent: BuilderUtils.getCodesetInExpression()
        """
        operator = "not" if is_exclusion else ""
        return BuilderUtils.CODESET_IN_TEMPLATE.format(operator, column_name, codeset_id)
    
    @staticmethod
    def get_concept_ids_from_concepts(concepts: List[Concept]) -> List[int]:
        """Get concept IDs from concept list.
        
        Java equivalent: BuilderUtils.getConceptIdsFromConcepts()
        """
        return [concept.concept_id for concept in concepts if concept.concept_id is not None]
    
    @staticmethod
    def get_operator(op: str) -> str:
        """Get SQL operator for range comparison.
        
        Java equivalent: BuilderUtils.getOperator(String op)
        """
        operators = {
            "lt": "<",
            "lte": "<=",
            "eq": "=",
            "!eq": "<>",
            "gt": ">",
            "gte": ">="
        }
        if op in operators:
            return operators[op]
        raise RuntimeError(f"Unknown operator type: {op}")

    @staticmethod
    def build_date_range_clause(sql_expression: str, date_range: Optional[DateRange]) -> Optional[str]:
        """Build date range clause for SQL.
        
        Java equivalent: BuilderUtils.buildDateRangeClause(String sqlExpression, DateRange range)
        """
        if date_range is None or date_range.op is None:
            return None
        
        op = date_range.op.lower()
        
        # Handle "bt" (between) operator
        if op.endswith("bt"):
            negation = "not " if op.startswith("!") else ""
            return f"{negation}({sql_expression} >= {BuilderUtils.date_string_to_sql(date_range.value)} and {sql_expression} <= {BuilderUtils.date_string_to_sql(date_range.extent)})"
        
        # Handle other operators
        if date_range.value is None:
            return None
            
        return f"{sql_expression} {BuilderUtils.get_operator(op)} {BuilderUtils.date_string_to_sql(date_range.value)}"
    
    @staticmethod
    def build_numeric_range_clause(sql_expression: str, numeric_range: Optional[NumericRange], format: Optional[str] = None) -> Optional[str]:
        """Build numeric range clause for SQL.
        
        Java equivalent: BuilderUtils.buildNumericRangeClause(String sqlExpression, NumericRange range, String format)
        or buildNumericRangeClause(String sqlExpression, NumericRange range)
        """
        if numeric_range is None or numeric_range.op is None:
            return None
        
        op = numeric_range.op.lower()
        
        if op.endswith("bt"):
            if numeric_range.value is None or numeric_range.extent is None:
                return None
            negation = "not " if op.startswith("!") else ""
            if format:
                # Double range (decimal)
                val_str = f"{float(numeric_range.value):{format}}"
                extent_str = f"{float(numeric_range.extent):{format}}"
                return f"{negation}({sql_expression} >= {val_str} and {sql_expression} <= {extent_str})"
            else:
                # Integer range
                return f"{negation}({sql_expression} >= {int(numeric_range.value)} and {sql_expression} <= {int(numeric_range.extent)})"
        else:
            if numeric_range.value is None:
                return None
                
            if format:
                val_str = f"{float(numeric_range.value):{format}}"
                return f"{sql_expression} {BuilderUtils.get_operator(op)} {val_str}"
            else:
                return f"{sql_expression} {BuilderUtils.get_operator(op)} {int(numeric_range.value)}"
    
    @staticmethod
    def build_text_filter_clause(text_filter: Optional[Any], column_name: str) -> Optional[str]:
        """Build text filter clause for SQL.
        
        Java equivalent: BuilderUtils.buildTextFilterClause()
        """
        if text_filter is None:
            return None
        
        # Handle simple string (legacy/direct usage)
        if isinstance(text_filter, str):
            return f"{column_name} LIKE '%{text_filter}%'"
            
        # Handle TextFilter object
        # Note: We use hasattr/getattr because we might not have the type imported directly involved in circular imports
        text = getattr(text_filter, 'text', None)
        op = getattr(text_filter, 'op', 'contains')
        
        if text is None:
            return None
            
        # Escape single quotes in text
        text = text.replace("'", "''")
        
        if op == "eq": 
             return f"{column_name} = '{text}'"
        elif op == "!eq":
             return f"{column_name} <> '{text}'"
        elif op == "startsWith":
             return f"{column_name} LIKE '{text}%'"
        elif op == "endsWith":
             return f"{column_name} LIKE '%{text}'"
        elif op == "contains":
             return f"{column_name} LIKE '%{text}%'"
        elif op == "!contains":
             return f"{column_name} NOT LIKE '%{text}%'"
        else:
             # Default to exact match
             return f"{column_name} = '{text}'"
    
    @staticmethod
    def split_in_clause(column_name: str, values: List[int], max_length: int = 1000) -> str:
        """Split IN clause for large value lists.
        
        Java equivalent: BuilderUtils.splitInClause()
        """
        if not values:
            return "NULL"
        
        # Split into chunks
        chunks = []
        for i in range(0, len(values), max_length):
            chunk_values = values[i:i + max_length]
            chunk_clause = f"{column_name} in ({','.join(map(str, chunk_values))})"
            chunks.append(chunk_clause)
        
        # Java implementation always wraps the result in parentheses
        return f"({' or '.join(chunks)})"
    
    @staticmethod
    def date_string_to_sql(date_string: str) -> str:
        """Convert date string to SQL format (DATEFROMPARTS).
        
        Java equivalent: BuilderUtils.dateStringToSql()
        """
        parts = date_string.split('-')
        if len(parts) != 3:
            raise ValueError(f"Invalid date format: {date_string}. Expected YYYY-MM-DD.")
        return f"DATEFROMPARTS({int(parts[0])}, {int(parts[1])}, {int(parts[2])})"
