"""
Criteria classes for cohort definition.

This module contains classes for defining various types of criteria used in cohort expressions.
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from ..vocabulary.concept import Concept
from .core import DateAdjustment, CriteriaGroup, DateRange, NumericRange, ConceptSetSelection


class CriteriaColumn(BaseModel):
    """Represents a criteria column.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CriteriaColumn
    """
    # This would need to be defined based on the actual Java implementation
    pass


class Occurrence(BaseModel):
    """Represents occurrence settings for criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Occurrence
    """
    at_most: int = Field(alias="AT_MOST")
    at_least: int = Field(alias="AT_LEAST")
    count_column: Optional[CriteriaColumn] = Field(default=None, alias="countColumn")
    is_distinct: bool = Field(alias="isDistinct")
    type: int
    exactly: int = Field(alias="EXACTLY")
    count: int

    model_config = ConfigDict(populate_by_name=True)


class CorelatedCriteria(BaseModel):
    """Represents correlated criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CorelatedCriteria
    """
    occurrence: Optional[Occurrence] = None


class DemographicCriteria(BaseModel):
    """Represents demographic criteria for cohort definition.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DemographicCriteria
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    race: Optional[List[Concept]] = None
    ethnicity_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ethnicityCS")
    age: Optional[NumericRange] = None
    race_cs: Optional[ConceptSetSelection] = Field(default=None, alias="raceCS")
    ethnicity: Optional[List[Concept]] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class Criteria(BaseModel):
    """Represents a criteria with date adjustment and correlated criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Criteria
    """
    date_adjustment: Optional[DateAdjustment] = Field(default=None, alias="dateAdjustment")
    correlated_criteria: Optional[CriteriaGroup] = Field(default=None, alias="CorrelatedCriteria")
    include: Optional[str] = None  # JsonTypeInfo.Id.NAME


class InclusionRule(BaseModel):
    """Represents an inclusion rule for cohort definition.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.InclusionRule
    """
    expression: Optional[CriteriaGroup] = None
    description: Optional[str] = None
    name: Optional[str] = None
