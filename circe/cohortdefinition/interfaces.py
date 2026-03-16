"""
Interfaces for SQL query generation.

This module contains the interfaces that define contracts for SQL generation
in cohort definition queries.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from abc import ABC, abstractmethod
from typing import Optional, Union

from .builders.utils import BuilderOptions
from .core import CustomEraStrategy, DateOffsetStrategy
from .criteria import (
    ConditionEra,
    ConditionOccurrence,
    Death,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
    LocationRegion,
    Measurement,
    Observation,
    ObservationPeriod,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
    VisitOccurrence,
)

# Type alias for all criteria types
Criteria = Union[
    LocationRegion,
    ConditionEra,
    ConditionOccurrence,
    Death,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
    Measurement,
    Observation,
    ObservationPeriod,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    VisitOccurrence,
    VisitDetail,
]


class IGetCriteriaSqlDispatcher(ABC):
    """Interface for dispatching SQL generation for different criteria types.

    Java equivalent: org.ohdsi.circe.cohortdefinition.IGetCriteriaSqlDispatcher
    """

    @abstractmethod
    def get_criteria_sql(self, criteria: Criteria, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for various criteria types.

        Args:
            criteria: Any supported criteria type (LocationRegion, ConditionEra, etc.)
            options: Optional builder options

        Returns:
            SQL string for the criteria
        """
        pass


# Type alias for end strategies
EndStrategy = Union[DateOffsetStrategy, CustomEraStrategy]


class IGetEndStrategySqlDispatcher(ABC):
    """Interface for dispatching SQL generation for end strategies.

    Java equivalent: org.ohdsi.circe.cohortdefinition.IGetEndStrategySqlDispatcher
    """

    @abstractmethod
    def get_strategy_sql(self, strategy: EndStrategy, event_table: str) -> str:
        """Generate SQL for end strategies.

        Args:
            strategy: DateOffsetStrategy or CustomEraStrategy
            event_table: The event table name

        Returns:
            SQL string for the strategy
        """
        pass
