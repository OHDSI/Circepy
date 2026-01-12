"""
Cohort Definition Module

This module contains classes for defining cohort expressions, criteria, and related structures.
It mirrors the Java CIRCE-BE cohortdefinition package structure.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .cohort import CohortExpression
from .criteria import (
    Criteria, CorelatedCriteria, DemographicCriteria, 
    Occurrence, CriteriaColumn, InclusionRule,
    # Moved from core
    CriteriaGroup, PrimaryCriteria, WindowedCriteria,
    # Criteria Domain Classes
    ConditionOccurrence, DrugExposure, ProcedureOccurrence,
    VisitOccurrence, Observation, Measurement, DeviceExposure,
    Specimen, Death, VisitDetail, ObservationPeriod,
    PayerPlanPeriod, LocationRegion,
    # Era Criteria Classes
    ConditionEra, DrugEra, DoseEra,
    # Geographic Criteria
    GeoCriteria
)
from .core import (
    CollapseType, DateType, ResultLimit, Period, DateRange, 
    NumericRange, DateAdjustment, ObservationFilter, 
    CollapseSettings, EndStrategy, ConceptSetSelection,
    # Supporting Classes
    TextFilter, WindowBound, Window,
    DateOffsetStrategy, CustomEraStrategy
)
from .cohort_expression_query_builder import CohortExpressionQueryBuilder, BuildExpressionQueryOptions
from .concept_set_expression_query_builder import ConceptSetExpressionQueryBuilder
from .interfaces import IGetCriteriaSqlDispatcher, IGetEndStrategySqlDispatcher
from .printfriendly import MarkdownRender

__all__ = [
    # Main cohort class
    "CohortExpression",
    
    # Criteria classes
    "Criteria", "CorelatedCriteria", "DemographicCriteria", 
    "Occurrence", "CriteriaColumn", "InclusionRule",
    
    # Criteria Domain Classes
    "ConditionOccurrence", "DrugExposure", "ProcedureOccurrence",
    "VisitOccurrence", "Observation", "Measurement", "DeviceExposure",
    "Specimen", "Death", "VisitDetail", "ObservationPeriod",
    "PayerPlanPeriod", "LocationRegion",
    
    # Era Criteria Classes
    "ConditionEra", "DrugEra", "DoseEra",
    
    # Geographic Criteria
    "GeoCriteria",
    
    # Core classes
    "CollapseType", "DateType", "ResultLimit", "Period", "DateRange", 
    "NumericRange", "DateAdjustment", "ObservationFilter", 
    "CollapseSettings", "EndStrategy", "PrimaryCriteria", 
    "CriteriaGroup", "ConceptSetSelection",
    
    # Supporting Classes
    "TextFilter", "WindowBound", "Window", "WindowedCriteria",
    "DateOffsetStrategy", "CustomEraStrategy",
    
    # Query Builders
    "CohortExpressionQueryBuilder", "BuildExpressionQueryOptions",
    "ConceptSetExpressionQueryBuilder",
    
    # Interfaces
    "IGetCriteriaSqlDispatcher", "IGetEndStrategySqlDispatcher",
    
    # Print-Friendly
    "MarkdownRender"
]

# Rebuild models with forward references after all imports are complete
CriteriaGroup.model_rebuild()
PrimaryCriteria.model_rebuild()
WindowedCriteria.model_rebuild()
CorelatedCriteria.model_rebuild()
CohortExpression.model_rebuild()
