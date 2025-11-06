"""
Core cohort definition classes.

This module contains the fundamental classes for defining cohort expressions and their components.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Union, Any, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator, Discriminator, AliasChoices
from enum import Enum
from .utils import to_pascal_alias

if TYPE_CHECKING:
    from .criteria import DemographicCriteria
else:
    # Import at runtime to avoid circular imports
    DemographicCriteria = 'DemographicCriteria'


class CollapseType(str, Enum):
    """Enumeration for collapse types.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CollapseType
    
    Note: Java enum only has ERA, but Python also supports collapse/no_collapse
    for backward compatibility and future use.
    """
    ERA = "ERA"
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
    type: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("Type", "type"),
        serialization_alias="Type"
    )


class Period(BaseModel):
    """Represents a time period with start and end dates.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Period
    """
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_pascal_alias
    )


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
    op: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("Op", "op"),
        serialization_alias="Op"
    )
    value: Optional[Union[int, float]] = Field(
        default=None,
        validation_alias=AliasChoices("Value", "value"),
        serialization_alias="Value"
    )
    extent: Optional[Union[int, float]] = Field(
        default=None,
        validation_alias=AliasChoices("Extent", "extent"),
        serialization_alias="Extent"
    )


class DateAdjustment(BaseModel):
    """Represents date adjustment settings.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DateAdjustment
    """
    start_offset: int
    end_offset: int
    start_with: Optional[DateType] = None
    end_with: Optional[DateType] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_pascal_alias
    )


class ObservationFilter(BaseModel):
    """Represents observation window filter settings.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ObservationFilter
    """
    prior_days: int = Field(
        validation_alias=AliasChoices("PriorDays", "priorDays"),
        serialization_alias="PriorDays"
    )
    post_days: int = Field(
        validation_alias=AliasChoices("PostDays", "postDays"),
        serialization_alias="PostDays"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class CollapseSettings(BaseModel):
    """Represents collapse settings for cohort expressions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CollapseSettings
    """
    era_pad: int = Field(
        validation_alias=AliasChoices("EraPad", "eraPad"),
        serialization_alias="EraPad"
    )
    collapse_type: Optional[CollapseType] = Field(
        default=None,
        validation_alias=AliasChoices("CollapseType", "collapseType"),
        serialization_alias="CollapseType"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class EndStrategy(BaseModel):
    """Represents the end strategy for cohort expressions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.EndStrategy
    """
    include: Optional[str] = None  # JsonTypeInfo.Id.NAME


class PrimaryCriteria(BaseModel):
    """Represents the primary criteria for cohort definition.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.PrimaryCriteria
    """
    criteria_list: Optional[List[Any]] = Field(
        default=None,
        validation_alias=AliasChoices("CriteriaList", "criteriaList"),
        serialization_alias="CriteriaList"
    )
    observation_window: Optional[ObservationFilter] = Field(
        default=None,
        validation_alias=AliasChoices("ObservationWindow", "observationWindow"),
        serialization_alias="ObservationWindow"
    )
    primary_limit: Optional[ResultLimit] = Field(
        default=None,
        validation_alias=AliasChoices("PrimaryCriteriaLimit", "primaryCriteriaLimit", "primaryLimit"),
        serialization_alias="PrimaryCriteriaLimit"
    )

    model_config = ConfigDict(populate_by_name=True)
    
    @field_validator('criteria_list', mode='before')
    @classmethod
    def deserialize_criteria_list(cls, v: Any) -> Any:
        """Deserialize criteria dicts in primary criteria.
        
        PrimaryCriteria.criteriaList contains Criteria[] in Java.
        JSON format: [{"ConditionOccurrence": {...}}] -> deserialize to ConditionOccurrence object
        """
        if not v or not isinstance(v, list):
            return v
        
        from .criteria import (
            ConditionOccurrence, DrugExposure, ProcedureOccurrence,
            VisitOccurrence, Observation, Measurement, DeviceExposure,
            Specimen, Death, VisitDetail, ObservationPeriod,
            PayerPlanPeriod, LocationRegion, ConditionEra,
            DrugEra, DoseEra
        )
        
        criteria_class_map = {
            'ConditionOccurrence': ConditionOccurrence,
            'DrugExposure': DrugExposure,
            'ProcedureOccurrence': ProcedureOccurrence,
            'VisitOccurrence': VisitOccurrence,
            'Observation': Observation,
            'Measurement': Measurement,
            'DeviceExposure': DeviceExposure,
            'Specimen': Specimen,
            'Death': Death,
            'VisitDetail': VisitDetail,
            'ObservationPeriod': ObservationPeriod,
            'PayerPlanPeriod': PayerPlanPeriod,
            'LocationRegion': LocationRegion,
            'ConditionEra': ConditionEra,
            'DrugEra': DrugEra,
            'DoseEra': DoseEra,
        }
        
        deserialized = []
        for item in v:
            if not isinstance(item, dict):
                deserialized.append(item)
                continue
            
            # JSON format: {"ConditionOccurrence": {...}} - unwrap and deserialize
            criteria_type = None
            criteria_data = None
            for key in item.keys():
                if key in criteria_class_map:
                    criteria_type = key
                    criteria_data = item[key]
                    break
            
            if criteria_type and criteria_data is not None:
                try:
                    # Make a copy to avoid modifying the original
                    criteria_data_copy = dict(criteria_data)
                    # Set default values for commonly missing required fields
                    # Use PascalCase keys since that's what's in the JSON
                    if criteria_type == 'Measurement' and 'MeasurementTypeExclude' not in criteria_data_copy and 'measurementTypeExclude' not in criteria_data_copy:
                        criteria_data_copy['MeasurementTypeExclude'] = False
                    if criteria_type == 'Observation' and 'ObservationTypeExclude' not in criteria_data_copy and 'observationTypeExclude' not in criteria_data_copy:
                        criteria_data_copy['ObservationTypeExclude'] = False
                    if criteria_type == 'ConditionOccurrence' and 'ConditionTypeExclude' not in criteria_data_copy and 'conditionTypeExclude' not in criteria_data_copy:
                        criteria_data_copy['ConditionTypeExclude'] = False
                    if 'First' not in criteria_data_copy and 'first' not in criteria_data_copy:
                        criteria_data_copy['First'] = False
                    
                    criteria_obj = criteria_class_map[criteria_type].model_validate(criteria_data_copy, strict=False)
                    deserialized.append(criteria_obj)
                except Exception as e:
                    # If deserialization fails, keep as dict
                    deserialized.append(item)
            else:
                # Not a recognized criteria type, keep as-is
                deserialized.append(item)
        
        return deserialized


class CriteriaGroup(BaseModel):
    """Represents a group of criteria with logical operators.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CriteriaGroup
    """
    criteria_list: Optional[List[Any]] = Field(
        default=None,
        validation_alias=AliasChoices("CriteriaList", "criteriaList"),
        serialization_alias="CriteriaList"
    )
    count: Optional[int] = None
    groups: Optional[List[Any]] = None
    demographic_criteria_list: Optional[List['DemographicCriteria']] = Field(
        default=None,
        validation_alias=AliasChoices("DemographicCriteriaList", "demographicCriteriaList"),
        serialization_alias="DemographicCriteriaList"
    )
    type: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("Type", "type"),
        serialization_alias="Type"
    )

    model_config = ConfigDict(populate_by_name=True)
    
    @field_validator('criteria_list', mode='before')
    @classmethod
    def deserialize_criteria_list(cls, v: Any) -> Any:
        """Deserialize criteria dicts to CorelatedCriteria objects.
        
        CriteriaGroup.criteriaList contains CorelatedCriteria[] in Java.
        JSON format: [{"Criteria": {"ConditionOccurrence": {...}}, "StartWindow": {...}, ...}]
        -> deserialize to CorelatedCriteria object
        """
        if not v or not isinstance(v, list):
            return v
        
        from .criteria import CorelatedCriteria
        
        def normalize_window(window_dict: dict) -> dict:
            """Normalize Window dict from Java JSON to Python model format."""
            if not isinstance(window_dict, dict):
                return window_dict
            normalized = {}
            # Normalize field names - Window uses aliases
            if 'UseEventEnd' in window_dict:
                normalized['useEventEnd'] = window_dict['UseEventEnd']
            elif 'useEventEnd' in window_dict:
                normalized['useEventEnd'] = window_dict['useEventEnd']
            if 'UseIndexEnd' in window_dict:
                normalized['useIndexEnd'] = window_dict['UseIndexEnd']
            elif 'useIndexEnd' in window_dict:
                normalized['useIndexEnd'] = window_dict['useIndexEnd']
            # Window model uses 'use_event_end' and 'use_index_end' as field names with aliases
            # but we need to use the aliases for validation
            if 'useEventEnd' in normalized:
                normalized['useEventEnd'] = normalized['useEventEnd']
            if 'useIndexEnd' in normalized:
                normalized['useIndexEnd'] = normalized['useIndexEnd']
            # Normalize Start/End to WindowBound format
            if 'Start' in window_dict:
                start = window_dict['Start']
                if isinstance(start, dict):
                    normalized['start'] = {
                        'coeff': start.get('Coeff') or start.get('coeff', 0),
                        'days': start.get('Days') or start.get('days')
                    }
                else:
                    normalized['start'] = start
            if 'End' in window_dict:
                end = window_dict['End']
                if isinstance(end, dict):
                    normalized['end'] = {
                        'coeff': end.get('Coeff') or end.get('coeff', 0),
                        'days': end.get('Days') or end.get('days')
                    }
                else:
                    normalized['end'] = end
            # Extract coeff from Start if available (required field)
            if 'coeff' not in normalized and 'start' in normalized:
                if isinstance(normalized['start'], dict) and 'coeff' in normalized['start']:
                    normalized['coeff'] = normalized['start']['coeff']
                else:
                    normalized['coeff'] = 0  # Default
            elif 'coeff' not in normalized:
                normalized['coeff'] = 0  # Default
            # Ensure useEventEnd is present (required)
            if 'useEventEnd' not in normalized:
                normalized['useEventEnd'] = False
            return normalized
        
        def deserialize_criteria_item(item: Any) -> Any:
            """Convert a criteria dict to CorelatedCriteria object."""
            if not isinstance(item, dict):
                return item
            
            # Create a copy to avoid modifying the original
            item_copy = dict(item)
            
            # Normalize Window fields if present
            if 'StartWindow' in item_copy:
                item_copy['StartWindow'] = normalize_window(item_copy['StartWindow'])
            elif 'startWindow' in item_copy:
                item_copy['StartWindow'] = normalize_window(item_copy['startWindow'])
                item_copy.pop('startWindow', None)
            if 'EndWindow' in item_copy:
                item_copy['EndWindow'] = normalize_window(item_copy['EndWindow'])
            elif 'endWindow' in item_copy:
                item_copy['EndWindow'] = normalize_window(item_copy['endWindow'])
                item_copy.pop('endWindow', None)
            
            # Check if already a CorelatedCriteria structure with "Criteria" or "criteria" field
            if 'Criteria' in item_copy or 'criteria' in item_copy:
                # Normalize "Criteria" to "criteria"
                if 'Criteria' in item_copy:
                    item_copy['criteria'] = item_copy.pop('Criteria')
                
                # Deserialize the inner criteria dict if it's still a dict
                if isinstance(item_copy.get('criteria'), dict):
                    criteria_dict = item_copy['criteria']
                    # Find the criteria type (ConditionOccurrence, DrugEra, etc.)
                    criteria_type = None
                    criteria_data = None
                    for key in criteria_dict.keys():
                        criteria_type = key
                        criteria_data = criteria_dict[key]
                        break
                    
                    if criteria_type and criteria_data:
                        # Try to deserialize the inner criteria to the specific type
                        from .criteria import (
                            ConditionOccurrence, DrugExposure, ProcedureOccurrence,
                            VisitOccurrence, Observation, Measurement, DeviceExposure,
                            Specimen, Death, VisitDetail, ObservationPeriod,
                            PayerPlanPeriod, LocationRegion, ConditionEra,
                            DrugEra, DoseEra
                        )
                        
                        criteria_class_map = {
                            'ConditionOccurrence': ConditionOccurrence,
                            'DrugExposure': DrugExposure,
                            'ProcedureOccurrence': ProcedureOccurrence,
                            'VisitOccurrence': VisitOccurrence,
                            'Observation': Observation,
                            'Measurement': Measurement,
                            'DeviceExposure': DeviceExposure,
                            'Specimen': Specimen,
                            'Death': Death,
                            'VisitDetail': VisitDetail,
                            'ObservationPeriod': ObservationPeriod,
                            'PayerPlanPeriod': PayerPlanPeriod,
                            'LocationRegion': LocationRegion,
                            'ConditionEra': ConditionEra,
                            'DrugEra': DrugEra,
                            'DoseEra': DoseEra,
                        }
                        
                        if criteria_type in criteria_class_map:
                            try:
                                # Make a copy to avoid modifying the original
                                criteria_data_copy = dict(criteria_data)
                                # Set default values for commonly missing required fields
                                # Note: Use PascalCase keys since that's what's in the JSON
                                if 'MeasurementTypeExclude' not in criteria_data_copy and 'measurementTypeExclude' not in criteria_data_copy and criteria_type == 'Measurement':
                                    criteria_data_copy['MeasurementTypeExclude'] = False
                                if 'ObservationTypeExclude' not in criteria_data_copy and 'observationTypeExclude' not in criteria_data_copy and criteria_type == 'Observation':
                                    criteria_data_copy['ObservationTypeExclude'] = False
                                if 'First' not in criteria_data_copy and 'first' not in criteria_data_copy:
                                    # Most criteria types require 'first' as bool, but some allow Optional[bool]
                                    # Set to False as default for required bool fields
                                    criteria_data_copy['First'] = False
                                # Deserialize the inner criteria
                                inner_criteria = criteria_class_map[criteria_type].model_validate(criteria_data_copy, strict=False)
                                item_copy['criteria'] = inner_criteria
                            except Exception as e:
                                # If deserialization fails, keep as dict
                                # This is usually due to missing required fields
                                pass
                
                # Normalize Occurrence field - CorelatedCriteria uses 'occurrence' (lowercase) as field name
                # but JSON may have 'Occurrence' (capital O)
                from .criteria import Occurrence
                if 'Occurrence' in item_copy:
                    # Move to lowercase key and deserialize
                    occ_data = item_copy.pop('Occurrence')
                    if isinstance(occ_data, dict):
                        # Occurrence uses aliases (Type, Count, IsDistinct) - pass through as-is
                        # Pydantic will handle the aliases
                        item_copy['occurrence'] = Occurrence.model_validate(occ_data)
                    else:
                        item_copy['occurrence'] = occ_data
                elif 'occurrence' not in item_copy:
                    # Ensure Occurrence is present if missing
                    item_copy['occurrence'] = Occurrence(type=Occurrence._AT_LEAST, count=1, is_distinct=False)
                
                # Validate as CorelatedCriteria
                try:
                    return CorelatedCriteria.model_validate(item_copy)
                except Exception as e:
                    # If validation fails, return as-is (may be incomplete)
                    return item
            
            # Check if it's a simple polymorphic criteria like {"ConditionOccurrence": {...}}
            # or has window fields indicating it's a CorelatedCriteria
            if 'StartWindow' in item_copy or 'EndWindow' in item_copy or 'RestrictVisit' in item_copy or 'IgnoreObservationPeriod' in item_copy:
                # Find the criteria type
                criteria_type = None
                criteria_data = None
                for key in item_copy.keys():
                    if key not in ['StartWindow', 'EndWindow', 'RestrictVisit', 'IgnoreObservationPeriod', 'Occurrence', 'criteria']:
                        criteria_type = key
                        criteria_data = item_copy[key]
                        break
                
                if criteria_type and criteria_data:
                    # Convert to CorelatedCriteria structure
                    corelated_dict = {
                        'criteria': {criteria_type: criteria_data}
                    }
                    if 'StartWindow' in item_copy:
                        corelated_dict['StartWindow'] = item_copy['StartWindow']
                    if 'EndWindow' in item_copy:
                        corelated_dict['EndWindow'] = item_copy['EndWindow']
                    if 'RestrictVisit' in item_copy:
                        corelated_dict['RestrictVisit'] = item_copy['RestrictVisit']
                    if 'IgnoreObservationPeriod' in item_copy:
                        corelated_dict['IgnoreObservationPeriod'] = item_copy['IgnoreObservationPeriod']
                    if 'Occurrence' in item_copy:
                        corelated_dict['Occurrence'] = item_copy['Occurrence']
                    elif 'occurrence' in item_copy:
                        corelated_dict['Occurrence'] = item_copy['occurrence']
                    else:
                        # Ensure Occurrence is present
                        from .criteria import Occurrence
                        corelated_dict['Occurrence'] = {'Type': Occurrence._AT_LEAST, 'Count': 1, 'IsDistinct': False}
                    
                    try:
                        return CorelatedCriteria.model_validate(corelated_dict)
                    except Exception:
                        return item
            else:
                # Simple polymorphic criteria like {"ConditionOccurrence": {...}}
                criteria_type = None
                criteria_data = None
                for key in item_copy.keys():
                    criteria_type = key
                    criteria_data = item_copy[key]
                    break
                
                if criteria_type and criteria_data:
                    # Convert to CorelatedCriteria structure
                    corelated_dict = {'criteria': {criteria_type: criteria_data}}
                    try:
                        return CorelatedCriteria.model_validate(corelated_dict)
                    except Exception:
                        return item
            
            return item
        
        deserialized = []
        for item in v:
            if not isinstance(item, dict):
                deserialized.append(item)
                continue
            
            deserialized_item = deserialize_criteria_item(item)
            deserialized.append(deserialized_item)
        
        return deserialized
    
    @field_validator('groups', mode='before')
    @classmethod
    def deserialize_groups(cls, v: Any) -> Any:
        """Deserialize groups recursively."""
        if not v or not isinstance(v, list):
            return v
        
        deserialized = []
        for group in v:
            if isinstance(group, dict):
                # Let Pydantic handle validation - it will call field validators
                deserialized.append(group)
            else:
                deserialized.append(group)
        
        return deserialized
    
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
    codeset_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("CodesetId", "codesetId"),
        serialization_alias="CodesetId"
    )
    is_exclusion: bool = Field(
        validation_alias=AliasChoices("IsExclusion", "isExclusion"),
        serialization_alias="IsExclusion"
    )

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
    coeff: int = Field(
        validation_alias=AliasChoices("Coeff", "coeff"),
        serialization_alias="Coeff"
    )
    days: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("Days", "days"),
        serialization_alias="Days"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class Window(BaseModel):
    """Represents a time window for criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Window
    """
    start: Optional[WindowBound] = Field(
        default=None,
        validation_alias=AliasChoices("Start", "start"),
        serialization_alias="Start"
    )
    end: Optional[WindowBound] = Field(
        default=None,
        validation_alias=AliasChoices("End", "end"),
        serialization_alias="End"
    )
    use_event_end: bool = Field(
        default=False,
        validation_alias=AliasChoices("UseEventEnd", "useEventEnd"),
        serialization_alias="UseEventEnd"
    )
    use_index_end: bool = Field(
        default=False,
        validation_alias=AliasChoices("UseIndexEnd", "useIndexEnd"),
        serialization_alias="UseIndexEnd"
    )

    model_config = ConfigDict(populate_by_name=True)


class WindowedCriteria(BaseModel):
    """Base class for windowed criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.WindowedCriteria
    """
    criteria: Any = Field(
        validation_alias=AliasChoices("Criteria", "criteria"),
        serialization_alias="Criteria"
    )  # Will be specific criteria type
    start_window: Optional[Window] = Field(
        default=None,
        validation_alias=AliasChoices("StartWindow", "startWindow"),
        serialization_alias="StartWindow"
    )
    end_window: Optional[Window] = Field(
        default=None,
        validation_alias=AliasChoices("EndWindow", "endWindow"),
        serialization_alias="EndWindow"
    )
    restrict_visit: bool = Field(
        default=False,
        validation_alias=AliasChoices("RestrictVisit", "restrictVisit"),
        serialization_alias="RestrictVisit"
    )
    ignore_observation_period: bool = Field(
        default=False,
        validation_alias=AliasChoices("IgnoreObservationPeriod", "ignoreObservationPeriod"),
        serialization_alias="IgnoreObservationPeriod"
    )

    model_config = ConfigDict(populate_by_name=True)


class DateOffsetStrategy(EndStrategy):
    """Date offset end strategy.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DateOffsetStrategy
    """
    offset: int
    date_field: str = Field(
        validation_alias=AliasChoices("DateField", "dateField"),
        serialization_alias="DateField"
    )

    model_config = ConfigDict(populate_by_name=True)
    
    def accept(self, dispatcher: Any, event_table: str) -> str:
        """Accept method for visitor pattern."""
        return dispatcher.get_strategy_sql(self, event_table)


class CustomEraStrategy(EndStrategy):
    """Custom era end strategy.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CustomEraStrategy
    """
    drug_codeset_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("DrugCodesetId", "drugCodesetId"),
        serialization_alias="DrugCodesetId"
    )
    gap_days: int = Field(
        validation_alias=AliasChoices("GapDays", "gapDays"),
        serialization_alias="GapDays"
    )
    offset: int

    model_config = ConfigDict(populate_by_name=True)
    
    def accept(self, dispatcher: Any, event_table: str) -> str:
        """Accept method for visitor pattern."""
        return dispatcher.get_strategy_sql(self, event_table)
