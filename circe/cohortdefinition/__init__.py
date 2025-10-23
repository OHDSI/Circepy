"""
Cohort Definition Module

This module contains classes for defining cohort expressions, criteria, and related structures.
It mirrors the Java CIRCE-BE cohortdefinition package structure.
"""

from .cohort import CohortExpression
from .criteria import (
    Criteria, CorelatedCriteria, DemographicCriteria, 
    Occurrence, CriteriaColumn, InclusionRule
)
from .core import (
    CollapseType, DateType, ResultLimit, Period, DateRange, 
    NumericRange, DateAdjustment, ObservationFilter, 
    CollapseSettings, EndStrategy, PrimaryCriteria, 
    CriteriaGroup, ConceptSetSelection
)

__all__ = [
    # Main cohort class
    "CohortExpression",
    
    # Criteria classes
    "Criteria", "CorelatedCriteria", "DemographicCriteria", 
    "Occurrence", "CriteriaColumn", "InclusionRule",
    
    # Core classes
    "CollapseType", "DateType", "ResultLimit", "Period", "DateRange", 
    "NumericRange", "DateAdjustment", "ObservationFilter", 
    "CollapseSettings", "EndStrategy", "PrimaryCriteria", 
    "CriteriaGroup", "ConceptSetSelection"
]
