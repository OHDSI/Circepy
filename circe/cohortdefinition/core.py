"""
Core cohort definition classes.

This module contains the fundamental classes for defining cohort expressions and their components.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Union, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class CollapseType(str, Enum):
    """Enumeration for collapse types.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CollapseType
    """
    COLLAPSE = "collapse"
    NO_COLLAPSE = "no_collapse"


class DateType(str, Enum):
    """Enumeration for date types.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DateType
    """
    START_DATE = "start_date"
    END_DATE = "end_date"


class ResultLimit(BaseModel):
    """Represents a result limit for cohort expressions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ResultLimit
    """
    type: Optional[str] = None


class Period(BaseModel):
    """Represents a time period with start and end dates.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Period
    """
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class DateRange(BaseModel):
    """Represents a date range with operation, extent, and value.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DateRange
    """
    op: Optional[str] = None
    extent: Optional[str] = None
    value: Optional[str] = None


class NumericRange(BaseModel):
    """Represents a numeric range with operation, value, and extent.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.NumericRange
    """
    op: Optional[str] = None
    value: Optional[Union[int, float]] = None
    extent: Optional[Union[int, float]] = None


class DateAdjustment(BaseModel):
    """Represents date adjustment settings.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DateAdjustment
    """
    start_offset: int
    end_offset: int
    start_with: Optional[DateType] = None
    end_with: Optional[DateType] = None


class ObservationFilter(BaseModel):
    """Represents observation window filter settings.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ObservationFilter
    """
    prior_days: int
    post_days: int


class CollapseSettings(BaseModel):
    """Represents collapse settings for cohort expressions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CollapseSettings
    """
    era_pad: int
    collapse_type: Optional[CollapseType] = None


class EndStrategy(BaseModel):
    """Represents the end strategy for cohort expressions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.EndStrategy
    """
    include: Optional[str] = None  # JsonTypeInfo.Id.NAME


class PrimaryCriteria(BaseModel):
    """Represents the primary criteria for cohort definition.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.PrimaryCriteria
    """
    criteria_list: Optional[List[Any]] = Field(default=None, alias="criteriaList")
    observation_window: Optional[ObservationFilter] = Field(default=None, alias="observationWindow")
    primary_limit: Optional[ResultLimit] = Field(default=None, alias="primaryLimit")

    model_config = ConfigDict(populate_by_name=True)


class CriteriaGroup(BaseModel):
    """Represents a group of criteria with logical operators.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CriteriaGroup
    """
    criteria_list: Optional[List[Any]] = Field(default=None, alias="criteriaList")
    count: Optional[int] = None
    groups: Optional[List[Any]] = None
    demographic_criteria_list: Optional[List[Any]] = Field(default=None, alias="demographicCriteriaList")
    type: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
    
    def is_empty(self) -> bool:
        """Check if the criteria group is empty."""
        return (
            not self.criteria_list or len(self.criteria_list) == 0
        ) and (
            not self.groups or len(self.groups) == 0
        ) and (
            not self.demographic_criteria_list or len(self.demographic_criteria_list) == 0
        )


class ConceptSetSelection(BaseModel):
    """Represents a concept set selection.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ConceptSetSelection
    """
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    is_exclusion: bool = Field(alias="isExclusion")

    model_config = ConfigDict(populate_by_name=True)


class TextFilter(BaseModel):
    """Represents text filtering capabilities.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.TextFilter
    """
    text: Optional[str] = None
    op: Optional[str] = None


class WindowBound(BaseModel):
    """Represents a window bound for time windows.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.WindowBound
    """
    coeff: int
    days: Optional[int] = None


class Window(BaseModel):
    """Represents a time window for criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Window
    """
    use_event_end: bool = Field(alias="useEventEnd")
    start: Optional[WindowBound] = None
    coeff: int
    days: Optional[int] = None
    end: Optional[WindowBound] = None

    model_config = ConfigDict(populate_by_name=True)


class WindowedCriteria(BaseModel):
    """Base class for windowed criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.WindowedCriteria
    """
    criteria: Any  # Will be specific criteria type
    window_start: Optional[Window] = Field(default=None, alias="windowStart")
    window_end: Optional[Window] = Field(default=None, alias="windowEnd")
    restrict_visit: bool = Field(default=False, alias="RestrictVisit")
    ignore_observation_period: bool = Field(default=False, alias="IgnoreObservationPeriod")

    model_config = ConfigDict(populate_by_name=True)


class DateOffsetStrategy(BaseModel):
    """Date offset end strategy.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DateOffsetStrategy
    """
    offset: int
    date_field: str = Field(alias="dateField")

    model_config = ConfigDict(populate_by_name=True)
    
    def accept(self, dispatcher: Any, event_table: str) -> str:
        """Accept method for visitor pattern."""
        return dispatcher.get_strategy_sql(self, event_table)


class CustomEraStrategy(BaseModel):
    """Custom era end strategy.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CustomEraStrategy
    """
    drug_codeset_id: Optional[int] = Field(default=None, alias="drugCodesetId")
    gap_days: int = Field(alias="gapDays")
    offset: int

    model_config = ConfigDict(populate_by_name=True)
    
    def accept(self, dispatcher: Any, event_table: str) -> str:
        """Accept method for visitor pattern."""
        return dispatcher.get_strategy_sql(self, event_table)
