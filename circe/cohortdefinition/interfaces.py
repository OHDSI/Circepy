"""
Interfaces for SQL query generation.

This module contains the interfaces that define contracts for SQL generation
in cohort definition queries.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from abc import ABC, abstractmethod
from typing import Optional
from .criteria import (
    LocationRegion, ConditionEra, ConditionOccurrence, Death, DeviceExposure,
    DoseEra, DrugEra, DrugExposure, Measurement, Observation, ObservationPeriod,
    PayerPlanPeriod, ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail
)
from .core import DateOffsetStrategy, CustomEraStrategy
from .builders.utils import BuilderOptions


class IGetCriteriaSqlDispatcher(ABC):
    """Interface for dispatching SQL generation for different criteria types.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.IGetCriteriaSqlDispatcher
    """
    
    @abstractmethod
    def get_criteria_sql(self, location_region: LocationRegion, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for location region criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, condition_era: ConditionEra, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for condition era criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, condition_occurrence: ConditionOccurrence, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for condition occurrence criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, death: Death, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for death criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, device_exposure: DeviceExposure, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for device exposure criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, dose_era: DoseEra, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for dose era criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, drug_era: DrugEra, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for drug era criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, drug_exposure: DrugExposure, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for drug exposure criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, measurement: Measurement, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for measurement criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, observation: Observation, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for observation criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, observation_period: ObservationPeriod, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for observation period criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, payer_plan_period: PayerPlanPeriod, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for payer plan period criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, procedure_occurrence: ProcedureOccurrence, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for procedure occurrence criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, specimen: Specimen, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for specimen criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, visit_occurrence: VisitOccurrence, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for visit occurrence criteria."""
        pass
    
    @abstractmethod
    def get_criteria_sql(self, visit_detail: VisitDetail, options: Optional[BuilderOptions] = None) -> str:
        """Generate SQL for visit detail criteria."""
        pass


class IGetEndStrategySqlDispatcher(ABC):
    """Interface for dispatching SQL generation for end strategies.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.IGetEndStrategySqlDispatcher
    """
    
    @abstractmethod
    def get_strategy_sql(self, strategy: DateOffsetStrategy, event_table: str) -> str:
        """Generate SQL for date offset strategy."""
        pass
    
    @abstractmethod
    def get_strategy_sql(self, strategy: CustomEraStrategy, event_table: str) -> str:
        """Generate SQL for custom era strategy."""
        pass
