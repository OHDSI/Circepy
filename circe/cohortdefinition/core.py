"""
Core cohort definition classes.

This module contains the fundamental classes for defining cohort expressions and their components.
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


class ConceptSetSelection(BaseModel):
    """Represents a concept set selection.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ConceptSetSelection
    """
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    is_exclusion: bool = Field(alias="isExclusion")

    model_config = ConfigDict(populate_by_name=True)
