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


class CriteriaColumn(str, Enum):
    """Enumeration for criteria columns.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.CriteriaColumn
    """
    DAYS_SUPPLY = "days_supply"
    DOMAIN_CONCEPT = "domain_concept"
    DOMAIN_SOURCE_CONCEPT = "domain_source_concept"
    DURATION = "duration"
    END_DATE = "end_date"
    ERA_OCCURRENCES = "occurrence_count"
    GAP_DAYS = "gap_days"
    QUANTITY = "quantity"
    RANGE_HIGH = "range_high"
    RANGE_LOW = "range_low"
    REFILLS = "refills"
    START_DATE = "start_date"
    UNIT = "unit_concept_id"
    VALUE_AS_NUMBER = "value_as_number"
    VISIT_ID = "visit_occurrence_id"
    VISIT_DETAIL_ID = "visit_detail_id"
    AGE = "age"
    GENDER = "gender"
    RACE = "race"
    ETHNICITY = "ethnicity"


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
    def build_date_range_clause(date_range: Optional[DateRange], column_name: str) -> Optional[str]:
        """Build date range clause for SQL.
        
        Java equivalent: BuilderUtils.buildDateRangeClause()
        """
        if date_range is None:
            return None
        
        # This would need to be implemented based on the Java logic
        # For now, return a placeholder
        return f"{column_name} {date_range.op} '{date_range.value}'"
    
    @staticmethod
    def build_numeric_range_clause(numeric_range: Optional[NumericRange], column_name: str) -> Optional[str]:
        """Build numeric range clause for SQL.
        
        Java equivalent: BuilderUtils.buildNumericRangeClause()
        """
        if numeric_range is None:
            return None
        
        op = numeric_range.op
        value = numeric_range.value
        extent = numeric_range.extent
        
        # Handle "bt" (between) operator
        if op == "bt" and extent is not None:
            # Always format with 4 decimal places to match R/Java output
            return f"({column_name} >= {float(value):.4f} and {column_name} <= {float(extent):.4f})"
        
        # Handle other operators
        if op == "lt":
            return f"{column_name} < {value}"
        elif op == "lte":
            return f"{column_name} <= {value}"
        elif op == "gt":
            return f"{column_name} > {value}"
        elif op == "gte":
            return f"{column_name} >= {value}"
        elif op == "eq":
            return f"{column_name} = {value}"
        elif op == "!eq":
            return f"{column_name} != {value}"
        else:
            # Fallback for unknown operators
            return f"{column_name} {op} {value}"
    
    @staticmethod
    def build_text_filter_clause(text_filter: Optional[str], column_name: str) -> Optional[str]:
        """Build text filter clause for SQL.
        
        Java equivalent: BuilderUtils.buildTextFilterClause()
        """
        if text_filter is None:
            return None
        
        return f"{column_name} LIKE '%{text_filter}%'"
    
    @staticmethod
    def split_in_clause(column_name: str, values: List[int], max_length: int = 1000) -> str:
        """Split IN clause for large value lists.
        
        Java equivalent: BuilderUtils.splitInClause()
        """
        if not values:
            return "NULL"
        
        if len(values) <= max_length:
            return ",".join(map(str, values))
        
        # Split into chunks
        chunks = []
        for i in range(0, len(values), max_length):
            chunk_values = values[i:i + max_length]
            chunk_clause = f"{column_name} IN ({','.join(map(str, chunk_values))})"
            chunks.append(chunk_clause)
        
        return " OR ".join(chunks)
    
    @staticmethod
    def date_string_to_sql(date_string: str) -> str:
        """Convert date string to SQL format.
        
        Java equivalent: BuilderUtils.dateStringToSql()
        """
        return f"'{date_string}'"
