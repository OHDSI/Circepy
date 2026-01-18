"""
Core cohort definition classes.

This module contains the fundamental classes for defining cohort expressions and their components.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Union, Any, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator, Discriminator, AliasChoices, model_serializer
from enum import Enum
from .utils import to_pascal_alias


class CirceBaseModel(BaseModel):
    """Base model for all Circe definitions to ensure consistent JSON serialization."""

    def model_dump_json(self, **kwargs):
        """Override model_dump_json to enforce Circe defaults."""
        kwargs.setdefault('by_alias', True)
        kwargs.setdefault('exclude_none', True)
        return super().model_dump_json(**kwargs)

    def model_dump(self, **kwargs):
        """Override model_dump to enforce Circe defaults."""
        kwargs.setdefault('by_alias', True)
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)

    model_config = ConfigDict(
        alias_generator=to_pascal_alias,
        populate_by_name=True,
        # Allow extra fields to prevent validation errors on unknown fields
        extra='ignore' 
    )



class CollapseType(str, Enum):
    """Enumeration for collapse types.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CollapseType
    
    Note: Java enum only has ERA, but Python also supports collapse/no_collapse
    for backward compatibility and future use.
    """
    ERA = "ERA"
    COLLAPSE = "collapse"
    NO_COLLAPSE = "no_collapse"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.name.upper() == value.upper() or member.value.upper() == value.upper():
                    return member
        return super()._missing_(value)


class DateType(str, Enum):
    """Enumeration for date types.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DateType
    """
    START_DATE = "start_date"
    END_DATE = "end_date"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.name.upper() == value.upper() or member.value.upper() == value.upper():
                    return member
        return super()._missing_(value)


class ResultLimit(CirceBaseModel):
    """Represents a result limit for cohort expressions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ResultLimit
    """
    type: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("Type", "type"),
        serialization_alias="Type"
    )


class Period(CirceBaseModel):
    """Represents a time period with start and end dates.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Period
    """
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_pascal_alias
    )


class DateRange(CirceBaseModel):
    """Represents a date range with operation, extent, and value.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DateRange
    """
    op: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("Op", "op"),
        serialization_alias="Op"
    )
    value: Optional[Union[str, float]] = Field(
        default=None,
        validation_alias=AliasChoices("Value", "value"),
        serialization_alias="Value"
    )
    extent: Optional[Union[str, float]] = Field(
        default=None,
        validation_alias=AliasChoices("Extent", "extent"),
        serialization_alias="Extent"
    )


class NumericRange(CirceBaseModel):
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


class DateAdjustment(CirceBaseModel):
    """Represents date adjustment settings.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DateAdjustment
    """
    start_offset: int = Field(
        validation_alias=AliasChoices("startOffset", "StartOffset"),
        serialization_alias="startOffset"
    )
    end_offset: int = Field(
        validation_alias=AliasChoices("endOffset", "EndOffset"),
        serialization_alias="endOffset"
    )
    start_with: Optional[DateType] = Field(
        default=DateType.START_DATE,
        validation_alias=AliasChoices("startWith", "StartWith"),
        serialization_alias="startWith"
    )
    end_with: Optional[DateType] = Field(
        default=DateType.END_DATE,
        validation_alias=AliasChoices("endWith", "EndWith"),
        serialization_alias="endWith"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class ObservationFilter(CirceBaseModel):
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


class CollapseSettings(CirceBaseModel):
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


class EndStrategy(CirceBaseModel):
    """Represents the end strategy for cohort expressions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.EndStrategy
    """
    include: Optional[str] = None  # JsonTypeInfo.Id.NAME

    @model_serializer(mode='wrap')
    def _serialize_polymorphic(self, serializer, info):
        """Serialize with polymorphic type wrapper for Java compatibility."""
        data = serializer(self)
        if self.__class__.__name__ == 'DateOffsetStrategy':
            return {'DateOffset': data}
        if self.__class__.__name__ == 'CustomEraStrategy':
            return {'CustomEra': data}
        return data




class ConceptSetSelection(CirceBaseModel):
    """Represents a concept set selection.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ConceptSetSelection
    """
    codeset_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("CodesetId", "codesetId"),
        serialization_alias="CodesetId"
    )
    is_exclusion: bool = Field(
        default=False,
        validation_alias=AliasChoices("IsExclusion", "isExclusion"),
        serialization_alias="IsExclusion"
    )

    model_config = ConfigDict(populate_by_name=True)


class TextFilter(CirceBaseModel):
    """Represents text filtering capabilities.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.TextFilter
    """
    text: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("Text", "text"),
        serialization_alias="Text"
    )
    op: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("Op", "op"),
        serialization_alias="Op"
    )


class WindowBound(CirceBaseModel):
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


class Window(CirceBaseModel):
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
    use_event_end: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("UseEventEnd", "useEventEnd"),
        serialization_alias="UseEventEnd"
    )
    use_index_end: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("UseIndexEnd", "useIndexEnd"),
        serialization_alias="UseIndexEnd"
    )

    model_config = ConfigDict(populate_by_name=True)




class DateOffsetStrategy(EndStrategy):
    """Date offset end strategy.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DateOffsetStrategy
    """
    offset: int = Field(
        validation_alias=AliasChoices("Offset", "offset"),
        serialization_alias="Offset"
    )
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
        default=0,
        validation_alias=AliasChoices("GapDays", "gapDays"),
        serialization_alias="GapDays"
    )
    offset: int = Field(
        default=0,
        validation_alias=AliasChoices("Offset", "offset"),
        serialization_alias="Offset"
    )
    days_supply_override: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("DaysSupplyOverride", "daysSupplyOverride"),
        serialization_alias="DaysSupplyOverride"
    )

    model_config = ConfigDict(populate_by_name=True)
    
    def accept(self, dispatcher: Any, event_table: str) -> str:
        """Accept method for visitor pattern."""
        return dispatcher.get_strategy_sql(self, event_table)
