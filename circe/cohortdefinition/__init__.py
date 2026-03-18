"""
Cohort Definition Module

This module contains classes for defining cohort expressions, criteria, and related structures.
It mirrors the Java CIRCE-BE cohortdefinition package structure.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .cohort import CohortExpression
from .cohort_expression_query_builder import (
    BuildExpressionQueryOptions,
    CohortExpressionQueryBuilder,
)
from .concept_set_expression_query_builder import ConceptSetExpressionQueryBuilder
from .core import (  # Supporting Classes
    CollapseSettings,
    CollapseType,
    ConceptSetSelection,
    CustomEraStrategy,
    DateAdjustment,
    DateOffsetStrategy,
    DateRange,
    DateType,
    EndStrategy,
    NumericRange,
    ObservationFilter,
    Period,
    ResultLimit,
    TextFilter,
    Window,
    WindowBound,
)
from .criteria import (  # Moved from core; Criteria Domain Classes; Era Criteria Classes; Geographic Criteria
    ConditionEra,
    ConditionOccurrence,
    CorelatedCriteria,
    Criteria,
    CriteriaColumn,
    CriteriaGroup,
    Death,
    DemographicCriteria,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
    GeoCriteria,
    InclusionRule,
    LocationRegion,
    Measurement,
    Observation,
    ObservationPeriod,
    Occurrence,
    PayerPlanPeriod,
    PrimaryCriteria,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
    VisitOccurrence,
    WindowedCriteria,
)
from .interfaces import IGetCriteriaSqlDispatcher, IGetEndStrategySqlDispatcher
from .printfriendly import MarkdownRender
from .validators import (
    get_censoring_criteria_types,
    get_concept_set_count,
    get_end_strategy_type,
    get_exclusion_count,
    get_primary_criteria_types,
    get_primary_limit_type,
    has_additional_criteria,
    has_censoring_criteria,
    has_concept_sets,
    has_end_strategy,
    has_exclusion_rules,
    has_inclusion_rule_by_name,
    has_observation_window,
    is_first_event,
)

__all__ = [
    # Main cohort class
    "CohortExpression",
    # Criteria classes
    "Criteria",
    "CorelatedCriteria",
    "DemographicCriteria",
    "Occurrence",
    "CriteriaColumn",
    "InclusionRule",
    # Criteria Domain Classes
    "ConditionOccurrence",
    "DrugExposure",
    "ProcedureOccurrence",
    "VisitOccurrence",
    "Observation",
    "Measurement",
    "DeviceExposure",
    "Specimen",
    "Death",
    "VisitDetail",
    "ObservationPeriod",
    "PayerPlanPeriod",
    "LocationRegion",
    # Era Criteria Classes
    "ConditionEra",
    "DrugEra",
    "DoseEra",
    # Geographic Criteria
    "GeoCriteria",
    # Core classes
    "CollapseType",
    "DateType",
    "ResultLimit",
    "Period",
    "DateRange",
    "NumericRange",
    "DateAdjustment",
    "ObservationFilter",
    "CollapseSettings",
    "EndStrategy",
    "PrimaryCriteria",
    "CriteriaGroup",
    "ConceptSetSelection",
    # Supporting Classes
    "TextFilter",
    "WindowBound",
    "Window",
    "WindowedCriteria",
    "DateOffsetStrategy",
    "CustomEraStrategy",
    # Query Builders
    "CohortExpressionQueryBuilder",
    "BuildExpressionQueryOptions",
    "ConceptSetExpressionQueryBuilder",
    # Interfaces
    "IGetCriteriaSqlDispatcher",
    "IGetEndStrategySqlDispatcher",
    # Print-Friendly
    "MarkdownRender",
    # Validator Functions
    "is_first_event",
    "has_exclusion_rules",
    "has_inclusion_rule_by_name",
    "get_exclusion_count",
    "has_censoring_criteria",
    "get_censoring_criteria_types",
    "has_additional_criteria",
    "has_end_strategy",
    "get_end_strategy_type",
    "get_primary_criteria_types",
    "has_observation_window",
    "get_primary_limit_type",
    "get_concept_set_count",
    "has_concept_sets",
]

# Rebuild models with forward references after all imports are complete
CriteriaGroup.model_rebuild()
PrimaryCriteria.model_rebuild()
WindowedCriteria.model_rebuild()
CorelatedCriteria.model_rebuild()
CohortExpression.model_rebuild()
