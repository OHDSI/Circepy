"""
Criteria classes for cohort definition.

This module contains classes for defining various types of criteria used in cohort expressions.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Any, ClassVar, Union, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict, model_serializer, AliasChoices, field_validator
from enum import Enum
from ..vocabulary.concept import Concept
from .core import (
    DateAdjustment, DateRange, NumericRange, ConceptSetSelection,
    TextFilter, Window, Period, ResultLimit, ObservationFilter,
    CollapseSettings, EndStrategy, CirceBaseModel
)


class CriteriaColumn(str, Enum):
    """Represents a criteria column.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.CriteriaColumn
    """
    DAYS_SUPPLY = "days_supply"
    DOMAIN_CONCEPT = "domain_concept_id"
    DOMAIN_SOURCE_CONCEPT = "domain_source_concept_id"
    DURATION = "duration"
    END_DATE = "end_date"
    ERA_OCCURRENCES = "occurrence_count"
    GAP_DAYS = "gap_days"
    QUANTITY = "quantity"
    RANGE_HIGH = "range_high"
    RANGE_LOW = "range_low"
    REFILLS = "refills"
    START_DATE = "start_date"
    UNIT = "unit_concept_id"
    VALUE_AS_NUMBER = "value_as_number"
    VISIT_ID = "visit_occurrence_id"
    VISIT_DETAIL_ID = "visit_detail_id"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            # Try to match by name (case-insensitive)
            for member in cls:
                if member.name.upper() == value.upper():
                    return member
            # Try to match by value (case-insensitive)
            for member in cls:
                if member.value.upper() == value.upper():
                    return member
            # Try to match partial matches if needed (e.g. DOMAIN_CONCEPT for domain_concept_id)
            if value.upper() == "DOMAIN_CONCEPT":
                return cls.DOMAIN_CONCEPT
            if value.upper() == "DOMAIN_SOURCE_CONCEPT":
                return cls.DOMAIN_SOURCE_CONCEPT
            if value.upper() == "UNIT":
                return cls.UNIT
            if value.upper() == "VISIT":
                return cls.VISIT_ID
                
        return super()._missing_(value)


class Occurrence(CirceBaseModel):
    """Represents occurrence settings for criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Occurrence
    
    Note: In Java, EXACTLY, AT_MOST, AT_LEAST are static final constants.
    The JSON schema extraction treats them as required fields, so we include
    them as required instance fields. They should always be set to their constant values.
    For class-level access, use the _EXACTLY, _AT_MOST, _AT_LEAST constants.
    """
    # Instance fields required by JSON schema (required fields)
    # These are required by schema - they represent constants but are fields in JSON
    # Default values are set to match the constant values for runtime convenience
    # EXCLUDED from serialization - these are constants, not exported to JSON
    AT_MOST: int = Field(default=1, alias="AT_MOST", exclude=True)
    AT_LEAST: int = Field(default=2, alias="AT_LEAST", exclude=True)
    EXACTLY: int = Field(default=0, alias="EXACTLY", exclude=True)
    
    type: int = Field(validation_alias=AliasChoices("Type", "type"), serialization_alias="Type")
    count: int = Field(validation_alias=AliasChoices("Count", "count"), serialization_alias="Count")
    is_distinct: bool = Field(default=False, validation_alias=AliasChoices("IsDistinct", "isDistinct"), serialization_alias="IsDistinct")
    count_column: Optional[CriteriaColumn] = Field(default=None, validation_alias=AliasChoices("CountColumn", "countColumn"), serialization_alias="CountColumn")

    model_config = ConfigDict(populate_by_name=True)

# Class-level constants for code access (matching Java static final)
# These are separate from instance fields to avoid shadowing
Occurrence._EXACTLY = 0
Occurrence._AT_MOST = 1
Occurrence._AT_LEAST = 2


class WindowedCriteria(CirceBaseModel):
    """Base class for windowed criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.WindowedCriteria
    """
    criteria: 'CriteriaType' = Field(
        validation_alias=AliasChoices("Criteria", "criteria"),
        serialization_alias="Criteria"
    )
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


class CorelatedCriteria(WindowedCriteria):
    """Represents correlated criteria.
    NOTE - this is a spelling mistake in the java implementation which leads to some confusion here.
    The class also doesn't appear to be used much (there is a CorrelationGroup class that may supersede it?
    Java equivalent: org.ohdsi.circe.cohortdefinition.CorelatedCriteria
    """
    occurrence: Optional[Occurrence] = Field(
        default=None,
        validation_alias=AliasChoices("Occurrence", "occurrence"),
        serialization_alias="Occurrence"
    )
    model_config = ConfigDict(populate_by_name=True)


class DemographicCriteria(CirceBaseModel):
    """Represents demographic criteria for cohort definition.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DemographicCriteria
    """
    gender: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("Gender", "gender"),
        serialization_alias="Gender"
    )
    occurrence_end_date: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("OccurrenceEndDate", "occurrenceEndDate"),
        serialization_alias="OccurrenceEndDate"
    )
    gender_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("GenderCS", "genderCS"),
        serialization_alias="GenderCS"
    )
    race: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("Race", "race"),
        serialization_alias="Race"
    )
    ethnicity_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("EthnicityCS", "ethnicityCS"),
        serialization_alias="EthnicityCS"
    )
    age: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("Age", "age"),
        serialization_alias="Age"
    )
    race_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("RaceCS", "raceCS"),
        serialization_alias="RaceCS"
    )
    ethnicity: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("Ethnicity", "ethnicity"),
        serialization_alias="Ethnicity"
    )
    occurrence_start_date: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("OccurrenceStartDate", "occurrenceStartDate"),
        serialization_alias="OccurrenceStartDate"
    )

    model_config = ConfigDict(populate_by_name=True)


class Criteria(CirceBaseModel):
    """Represents a criteria with date adjustment and correlated criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Criteria
    """
    date_adjustment: Optional[DateAdjustment] = Field(
        default=None,
        validation_alias=AliasChoices("DateAdjustment", "dateAdjustment"),
        serialization_alias="DateAdjustment"
    )
    correlated_criteria: Optional['CriteriaGroup'] = Field(
        default=None,
        validation_alias=AliasChoices("CorrelatedCriteria", "correlatedCriteria"),
        serialization_alias="CorrelatedCriteria"
    )
    include: Optional[str] = None  # JsonTypeInfo.Id.NAME
    
    @model_serializer(mode='wrap')
    def _serialize_polymorphic(self, serializer, info):
        """Serialize with polymorphic type wrapper for Java compatibility."""
        # Get the serialized data using default serialization
        data = serializer(self)
        # Wrap in class name for polymorphic deserialization in Java
        # Only wrap if this is a subclass (not the base Criteria class)
        if self.__class__.__name__ != 'Criteria':
            return {self.__class__.__name__: data}
        return data
    
    def accept(self, dispatcher: Any, options: Optional[Any] = None) -> str:
        """Accept method for visitor pattern."""
        return dispatcher.get_criteria_sql(self, options)


class InclusionRule(CirceBaseModel):
    """Represents an inclusion rule for cohort definition.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.InclusionRule
    """
    expression: Optional['CriteriaGroup'] = Field(
        default=None,
        validation_alias=AliasChoices("Expression", "expression"),
        serialization_alias="Expression"
    )
    description: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("Description", "description"),
        serialization_alias="Description"
    )
    name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("Name", "name"),
        serialization_alias="Name"
    )


# =============================================================================
# CRITERIA DOMAIN CLASSES
# =============================================================================

class ConditionOccurrence(Criteria):
    """Condition occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ConditionOccurrence
    """
    codeset_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("CodesetId", "codesetId"),
        serialization_alias="CodesetId"
    )
    first: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    occurrence_start_date: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("OccurrenceStartDate", "occurrenceStartDate"),
        serialization_alias="OccurrenceStartDate"
    )
    occurrence_end_date: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("OccurrenceEndDate", "occurrenceEndDate"),
        serialization_alias="OccurrenceEndDate"
    )
    condition_type: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ConditionType", "conditionType"),
        serialization_alias="ConditionType"
    )
    condition_type_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("ConditionTypeCS", "conditionTypeCS"),
        serialization_alias="ConditionTypeCS"
    )
    condition_type_exclude: Optional[bool] = Field(
        default=False,
        validation_alias=AliasChoices("ConditionTypeExclude", "conditionTypeExclude"),
        serialization_alias="ConditionTypeExclude"
    )
    stop_reason: Optional[TextFilter] = Field(
        default=None,
        validation_alias=AliasChoices("StopReason", "stopReason"),
        serialization_alias="StopReason"
    )
    condition_source_concept: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("ConditionSourceConcept", "conditionSourceConcept"),
        serialization_alias="ConditionSourceConcept"
    )
    age: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("Age", "age"),
        serialization_alias="Age"
    )
    gender: Optional[List[Concept]] = Field(
        default=None,
        serialization_alias="gender"
    )
    gender_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("GenderCS", "genderCS"),
        serialization_alias="GenderCS"
    )
    provider_specialty: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ProviderSpecialty", "providerSpecialty"),
        serialization_alias="ProviderSpecialty"
    )
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("ProviderSpecialtyCS", "providerSpecialtyCS"),
        serialization_alias="ProviderSpecialtyCS"
    )
    visit_type: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("VisitType", "visitType"),
        serialization_alias="VisitType"
    )
    visit_type_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("VisitTypeCS", "visitTypeCS"),
        serialization_alias="VisitTypeCS"
    )
    condition_status: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ConditionStatus", "conditionStatus"),
        serialization_alias="ConditionStatus"
    )
    condition_status_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("ConditionStatusCS", "conditionStatusCS"),
        serialization_alias="ConditionStatusCS"
    )
    date_adjustment: Optional[DateAdjustment] = Field(
        default=None,
        validation_alias=AliasChoices("DateAdjustment", "dateAdjustment"),
        serialization_alias="DateAdjustment"
    )

    model_config = ConfigDict(populate_by_name=True)


class DrugExposure(Criteria):
    """Drug exposure criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DrugExposure
    """
    gender: Optional[List[Concept]] = Field(
        default=None,
        serialization_alias="gender"
    )
    occurrence_end_date: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("OccurrenceEndDate", "occurrenceEndDate"),
        serialization_alias="OccurrenceEndDate"
    )
    stop_reason: Optional[TextFilter] = Field(
        default=None,
        validation_alias=AliasChoices("StopReason", "stopReason"),
        serialization_alias="StopReason"
    )
    drug_source_concept: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("DrugSourceConcept", "drugSourceConcept"),
        serialization_alias="DrugSourceConcept"
    )
    gender_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("GenderCS", "genderCS"),
        serialization_alias="GenderCS"
    )
    drug_type: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("DrugType", "drugType"),
        serialization_alias="DrugType"
    )
    drug_type_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("DrugTypeCS", "drugTypeCS"),
        serialization_alias="DrugTypeCS"
    )
    drug_type_exclude: bool = Field(
        default=False,
        validation_alias=AliasChoices("DrugTypeExclude", "drugTypeExclude"),
        serialization_alias="DrugTypeExclude"
    )
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("ProviderSpecialtyCS", "providerSpecialtyCS"),
        serialization_alias="ProviderSpecialtyCS"
    )
    visit_type_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("VisitTypeCS", "visitTypeCS"),
        serialization_alias="VisitTypeCS"
    )
    visit_type: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("VisitType", "visitType"),
        serialization_alias="VisitType"
    )
    route_concept: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("RouteConcept", "routeConcept"),
        serialization_alias="RouteConcept"
    )
    route_concept_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("RouteConceptCS", "routeConceptCS"),
        serialization_alias="RouteConceptCS"
    )
    codeset_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("CodesetId", "codesetId"),
        serialization_alias="CodesetId"
    )
    first: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    provider_specialty: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ProviderSpecialty", "providerSpecialty"),
        serialization_alias="ProviderSpecialty"
    )
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("OccurrenceStartDate", "occurrenceStartDate"),
        serialization_alias="OccurrenceStartDate"
    )
    dose_unit: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("DoseUnit", "doseUnit"),
        serialization_alias="DoseUnit"
    )
    dose_unit_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("DoseUnitCS", "doseUnitCS"),
        serialization_alias="DoseUnitCS"
    )
    lot_number: Optional[TextFilter] = Field(
        default=None,
        validation_alias=AliasChoices("LotNumber", "lotNumber"),
        serialization_alias="LotNumber"
    )
    quantity: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("Quantity", "quantity"),
        serialization_alias="Quantity"
    )
    days_supply: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("DaysSupply", "daysSupply"),
        serialization_alias="DaysSupply"
    )
    refills: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("Refills", "refills"),
        serialization_alias="Refills"
    )
    effective_drug_dose: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("EffectiveDrugDose", "effectiveDrugDose"),
        serialization_alias="EffectiveDrugDose"
    )

    model_config = ConfigDict(populate_by_name=True)


class ProcedureOccurrence(Criteria):
    """Procedure occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ProcedureOccurrence
    """
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="OccurrenceEndDate")
    procedure_source_concept: Optional[int] = Field(default=None, alias="ProcedureSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    procedure_type: Optional[List[Concept]] = Field(default=None, alias="ProcedureType")
    procedure_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ProcedureTypeCS")
    procedure_type_exclude: bool = Field(default=False, alias="ProcedureTypeExclude")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ProviderSpecialtyCS")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="VisitTypeCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="VisitType")
    modifier: Optional[List[Concept]] = Field(default=None, alias="Modifier")
    modifier_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ModifierCS")
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="ProviderSpecialty")
    age: Optional[NumericRange] = None
    quantity: Optional[NumericRange] = Field(default=None, alias="Quantity")
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="OccurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class VisitOccurrence(Criteria):
    """Visit occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.VisitOccurrence
    """
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: Optional[bool] = Field(default=None, alias="First")
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="OccurrenceEndDate")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="VisitType")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="VisitTypeCS")
    visit_type_exclude: bool = Field(default=False, alias="VisitTypeExclude")
    visit_source_concept: Optional[int] = Field(default=None, alias="VisitSourceConcept")
    visit_length: Optional[NumericRange] = Field(default=None, alias="VisitLength")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ProviderSpecialtyCS")
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="ProviderSpecialty")
    place_of_service: Optional[List[Concept]] = Field(default=None, alias="PlaceOfService")
    place_of_service_cs: Optional[ConceptSetSelection] = Field(default=None, alias="PlaceOfServiceCS")
    place_of_service_location: Optional[int] = Field(default=None, alias="PlaceOfServiceLocation")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="OccurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class Observation(Criteria):
    """Observation criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Observation
    """
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    occurrence_end_date: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("OccurrenceEndDate", "occurrenceEndDate"),
        serialization_alias="OccurrenceEndDate"
    )
    observation_source_concept: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("ObservationSourceConcept", "observationSourceConcept"),
        serialization_alias="ObservationSourceConcept"
    )
    gender_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("GenderCS", "genderCS"),
        serialization_alias="GenderCS"
    )
    observation_type: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ObservationType", "observationType"),
        serialization_alias="ObservationType"
    )
    observation_type_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("ObservationTypeCS", "observationTypeCS"),
        serialization_alias="ObservationTypeCS"
    )
    observation_type_exclude: bool = Field(
        default=False,
        validation_alias=AliasChoices("ObservationTypeExclude", "observationTypeExclude"),
        serialization_alias="ObservationTypeExclude"
    )
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("ProviderSpecialtyCS", "providerSpecialtyCS"),
        serialization_alias="ProviderSpecialtyCS"
    )
    visit_type_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("VisitTypeCS", "visitTypeCS"),
        serialization_alias="VisitTypeCS"
    )
    visit_type: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("VisitType", "visitType"),
        serialization_alias="VisitType"
    )
    value_as_number: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("ValueAsNumber", "valueAsNumber"),
        serialization_alias="ValueAsNumber"
    )
    unit: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("Unit", "unit"),
        serialization_alias="Unit"
    )
    unit_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("UnitCS", "unitCS"),
        serialization_alias="UnitCS"
    )
    value_as_concept: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ValueAsConcept", "valueAsConcept"),
        serialization_alias="ValueAsConcept"
    )
    value_as_concept_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("ValueAsConceptCS", "valueAsConceptCS"),
        serialization_alias="ValueAsConceptCS"
    )
    qualifier: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("Qualifier", "qualifier"),
        serialization_alias="Qualifier"
    )
    qualifier_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("QualifierCS", "qualifierCS"),
        serialization_alias="QualifierCS"
    )
    value_as_string: Optional[TextFilter] = Field(
        default=None,
        validation_alias=AliasChoices("ValueAsString", "valueAsString"),
        serialization_alias="ValueAsString"
    )
    codeset_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("CodesetId", "codesetId"),
        serialization_alias="CodesetId"
    )
    first: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    provider_specialty: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ProviderSpecialty", "providerSpecialty"),
        serialization_alias="ProviderSpecialty"
    )
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("OccurrenceStartDate", "occurrenceStartDate"),
        serialization_alias="OccurrenceStartDate"
    )

    model_config = ConfigDict(populate_by_name=True)


class Measurement(Criteria):
    """Measurement criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Measurement
    """
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="OccurrenceEndDate")
    measurement_source_concept: Optional[int] = Field(default=None, alias="MeasurementSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    measurement_type: Optional[List[Concept]] = Field(default=None, alias="MeasurementType")
    measurement_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="MeasurementTypeCS")
    measurement_type_exclude: bool = Field(
        default=False,
        validation_alias=AliasChoices("MeasurementTypeExclude", "measurementTypeExclude"),
        serialization_alias="MeasurementTypeExclude"
    )
    operator: Optional[List[Concept]] = None
    operator_cs: Optional[ConceptSetSelection] = Field(default=None, alias="OperatorCS")
    value_as_number: Optional[NumericRange] = Field(default=None, alias="ValueAsNumber")
    value_as_string: Optional[TextFilter] = Field(default=None, alias="ValueAsString")
    unit: Optional[List[Concept]] = Field(default=None, alias="Unit")
    unit_cs: Optional[ConceptSetSelection] = Field(default=None, alias="UnitCS")
    range_low: Optional[NumericRange] = Field(default=None, alias="RangeLow")
    range_high: Optional[NumericRange] = Field(default=None, alias="RangeHigh")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ProviderSpecialtyCS")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="VisitTypeCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="VisitType")
    codeset_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("CodesetId", "codesetId"),
        serialization_alias="CodesetId"
    )
    value_as_concept: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ValueAsConcept", "valueAsConcept"),
        serialization_alias="ValueAsConcept"
    )
    value_as_concept_cs: Optional[ConceptSetSelection] = Field(
        default=None,
        validation_alias=AliasChoices("ValueAsConceptCS", "valueAsConceptCS"),
        serialization_alias="ValueAsConceptCS"
    )
    abnormal: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("Abnormal", "abnormal"),
        serialization_alias="Abnormal"
    )
    range_low_ratio: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("RangeLowRatio", "rangeLowRatio"),
        serialization_alias="RangeLowRatio"
    )
    range_high_ratio: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("RangeHighRatio", "rangeHighRatio"),
        serialization_alias="RangeHighRatio"
    )
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="ProviderSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="OccurrenceStartDate")
    visits: Optional[List[Concept]] = None  # Placeholder if needed, but not in list
    visit_type: Optional[List[Concept]] = Field(default=None, alias="VisitType")
    
    first: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="ProviderSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="OccurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class DeviceExposure(Criteria):
    """Device exposure criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DeviceExposure
    """
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="OccurrenceEndDate")
    device_source_concept: Optional[int] = Field(default=None, alias="DeviceSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    device_type: Optional[List[Concept]] = Field(default=None, alias="DeviceType")
    device_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="DeviceTypeCS")
    device_type_exclude: bool = Field(default=False, alias="DeviceTypeExclude")
    unique_device_id: Optional[TextFilter] = Field(default=None, alias="UniqueDeviceId")
    quantity: Optional[NumericRange] = None
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ProviderSpecialtyCS")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="VisitTypeCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="VisitType")
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="ProviderSpecialty")
    age: Optional[NumericRange] = Field(default=None, alias="Age")
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="OccurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class Specimen(Criteria):
    """Specimen criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Specimen
    """
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="OccurrenceEndDate")
    specimen_source_concept: Optional[int] = Field(default=None, alias="SpecimenSourceConcept")
    source_id: Optional[TextFilter] = Field(default=None, alias="SourceId")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    specimen_type: Optional[List[Concept]] = Field(default=None, alias="SpecimenType")
    specimen_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="SpecimenTypeCS")
    specimen_type_exclude: bool = Field(default=False, alias="SpecimenTypeExclude")
    unit: Optional[List[Concept]] = None
    unit_cs: Optional[ConceptSetSelection] = Field(default=None, alias="UnitCS")
    anatomic_site: Optional[List[Concept]] = Field(default=None, alias="AnatomicSite")
    anatomic_site_cs: Optional[ConceptSetSelection] = Field(default=None, alias="AnatomicSiteCS")
    disease_status: Optional[List[Concept]] = Field(default=None, alias="DiseaseStatus")
    disease_status_cs: Optional[ConceptSetSelection] = Field(default=None, alias="DiseaseStatusCS")
    quantity: Optional[NumericRange] = None
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="OccurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class Death(Criteria):
    """Death criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Death
    """
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="OccurrenceEndDate")
    death_source_concept: Optional[int] = Field(default=None, alias="DeathSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    death_type: Optional[List[Concept]] = Field(default=None, alias="DeathType")
    death_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="DeathTypeCS")
    death_type_exclude: bool = Field(
        default=False,
        validation_alias=AliasChoices("DeathTypeExclude", "deathTypeExclude"),
        serialization_alias="DeathTypeExclude"
    )
    cause_source_concept: Optional[int] = Field(default=None, alias="CauseSourceConcept")
    cause_source_concept_cs: Optional[ConceptSetSelection] = Field(default=None, alias="CauseSourceConceptCS")
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")

    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="OccurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class VisitDetail(Criteria):
    """Visit detail criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.VisitDetail
    """
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: Optional[bool] = Field(default=None, alias="First")
    visit_detail_start_date: Optional[DateRange] = Field(default=None, alias="VisitDetailStartDate")
    visit_detail_end_date: Optional[DateRange] = Field(default=None, alias="VisitDetailEndDate")
    visit_detail_type: Optional[List[Concept]] = Field(default=None, alias="VisitDetailType")
    visit_detail_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="VisitDetailTypeCS")
    visit_detail_type_exclude: bool = Field(default=False, alias="VisitDetailTypeExclude")
    visit_detail_source_concept: Optional[int] = Field(default=None, alias="VisitDetailSourceConcept")
    visit_detail_length: Optional[NumericRange] = Field(default=None, alias="VisitDetailLength")
    age: Optional[NumericRange] = Field(default=None, alias="Age")
    gender: Optional[List[Concept]] = Field(
        default=None,
        serialization_alias="gender"
    )
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="ProviderSpecialty")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ProviderSpecialtyCS")
    place_of_service: Optional[List[Concept]] = Field(default=None, alias="PlaceOfService")
    place_of_service_cs: Optional[ConceptSetSelection] = Field(default=None, alias="PlaceOfServiceCS")
    place_of_service_location: Optional[int] = Field(default=None, alias="PlaceOfServiceLocation")
    discharge_to: Optional[List[Concept]] = Field(default=None, alias="DischargeTo")
    discharge_to_cs: Optional[ConceptSetSelection] = Field(default=None, alias="DischargeToCS")

    model_config = ConfigDict(populate_by_name=True)


class ObservationPeriod(Criteria):
    """Observation period criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ObservationPeriod
    """
    first: Optional[bool] = Field(default=None, alias="First")
    period_start_date: Optional[DateRange] = Field(default=None, alias="PeriodStartDate")
    period_end_date: Optional[DateRange] = Field(default=None, alias="PeriodEndDate")
    user_defined_period: Optional[Period] = Field(default=None, alias="UserDefinedPeriod")
    period_type: Optional[List[Concept]] = Field(default=None, alias="PeriodType")
    period_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="PeriodTypeCS")
    period_length: Optional[NumericRange] = Field(default=None, alias="PeriodLength")
    age_at_start: Optional[NumericRange] = Field(default=None, alias="AgeAtStart")
    age_at_end: Optional[NumericRange] = Field(default=None, alias="AgeAtEnd")

    model_config = ConfigDict(populate_by_name=True)


class PayerPlanPeriod(Criteria):
    """Payer plan period criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.PayerPlanPeriod
    """
    first: Optional[bool] = Field(default=None, alias="First")
    period_start_date: Optional[DateRange] = Field(default=None, alias="PeriodStartDate")
    period_end_date: Optional[DateRange] = Field(default=None, alias="PeriodEndDate")
    user_defined_period: Optional[Period] = Field(default=None, alias="UserDefinedPeriod")
    period_length: Optional[NumericRange] = Field(default=None, alias="PeriodLength")
    age_at_start: Optional[NumericRange] = Field(default=None, alias="AgeAtStart")
    age_at_end: Optional[NumericRange] = Field(default=None, alias="AgeAtEnd")
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    payer_concept: Optional[int] = Field(default=None, alias="PayerConcept")
    plan_concept: Optional[int] = Field(default=None, alias="PlanConcept")
    sponsor_concept: Optional[int] = Field(default=None, alias="SponsorConcept")
    stop_reason_concept: Optional[int] = Field(default=None, alias="StopReasonConcept")
    payer_source_concept: Optional[int] = Field(default=None, alias="PayerSourceConcept")
    plan_source_concept: Optional[int] = Field(default=None, alias="PlanSourceConcept")
    sponsor_source_concept: Optional[int] = Field(default=None, alias="SponsorSourceConcept")
    stop_reason_source_concept: Optional[int] = Field(default=None, alias="StopReasonSourceConcept")

    model_config = ConfigDict(populate_by_name=True)


class LocationRegion(Criteria):
    """Location region criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.LocationRegion
    """
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# ERA CRITERIA CLASSES
# =============================================================================

class ConditionEra(Criteria):
    """Condition era criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ConditionEra
    """
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    era_start_date: Optional[DateRange] = Field(default=None, alias="EraStartDate")
    era_end_date: Optional[DateRange] = Field(default=None, alias="EraEndDate")
    occurrence_count: Optional[NumericRange] = Field(default=None, alias="OccurrenceCount")
    era_length: Optional[NumericRange] = Field(default=None, alias="EraLength")
    age_at_start: Optional[NumericRange] = Field(default=None, alias="AgeAtStart")
    age_at_end: Optional[NumericRange] = Field(default=None, alias="AgeAtEnd")
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    date_adjustment: Optional[DateAdjustment] = Field(default=None, alias="DateAdjustment")

    model_config = ConfigDict(populate_by_name=True)


class DrugEra(Criteria):
    """Drug era criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DrugEra
    """
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    era_start_date: Optional[DateRange] = Field(default=None, alias="EraStartDate")
    era_end_date: Optional[DateRange] = Field(default=None, alias="EraEndDate")
    occurrence_count: Optional[NumericRange] = Field(default=None, alias="OccurrenceCount")
    gap_days: Optional[NumericRange] = Field(default=None, alias="GapDays")
    era_length: Optional[NumericRange] = Field(default=None, alias="EraLength")
    age_at_start: Optional[NumericRange] = Field(default=None, alias="AgeAtStart")
    age_at_end: Optional[NumericRange] = Field(default=None, alias="AgeAtEnd")
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    date_adjustment: Optional[DateAdjustment] = Field(default=None, alias="DateAdjustment")

    model_config = ConfigDict(populate_by_name=True)


class DoseEra(Criteria):
    """Dose era criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DoseEra
    """
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: Optional[bool] = Field(default=None, alias="First")
    era_start_date: Optional[DateRange] = Field(default=None, alias="EraStartDate")
    era_end_date: Optional[DateRange] = Field(default=None, alias="EraEndDate")
    unit: Optional[List[Concept]] = Field(default=None, alias="Unit")
    unit_cs: Optional[ConceptSetSelection] = Field(default=None, alias="UnitCS")
    dose_value: Optional[NumericRange] = Field(default=None, alias="DoseValue")
    era_length: Optional[NumericRange] = Field(default=None, alias="EraLength")
    age_at_start: Optional[NumericRange] = Field(default=None, alias="AgeAtStart")
    age_at_end: Optional[NumericRange] = Field(default=None, alias="AgeAtEnd")
    gender: Optional[List[Concept]] = Field(default=None, serialization_alias="gender")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# GEOGRAPHIC CRITERIA
# =============================================================================

class GeoCriteria(Criteria):
    """Base class for geographic criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.GeoCriteria
    """
    pass

# =============================================================================
# CRITERIA GROUP AND PRIMARY CRITERIA (Moved from core)
# =============================================================================

class CriteriaGroup(BaseModel):
    """Represents a group of criteria with logical operators.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CriteriaGroup
    """
    criteria_list: Optional[List['CorelatedCriteria']] = Field(
        default=None,
        validation_alias=AliasChoices("CriteriaList", "criteriaList"),
        serialization_alias="CriteriaList"
    )
    count: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("Count", "count"),
        serialization_alias="Count"
    )
    groups: Optional[List['CriteriaGroup']] = Field(
        default=None,
        validation_alias=AliasChoices("Groups", "groups"),
        serialization_alias="Groups"
    )
    demographic_criteria_list: Optional[List[DemographicCriteria]] = Field(
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

    def is_empty(self) -> bool:
        """Check if the criteria group is empty."""
        has_criteria = self.criteria_list and len(self.criteria_list) > 0
        has_groups = self.groups and len(self.groups) > 0
        has_demographic = self.demographic_criteria_list and len(self.demographic_criteria_list) > 0
        return not (has_criteria or has_groups or has_demographic)
    
    @field_validator('groups', mode='before')
    @classmethod
    def deserialize_groups(cls, v: Any) -> Any:
        # Same Logic as before, just local
        if not v or not isinstance(v, list):
            return v
        result = []
        for item in v:
            if isinstance(item, dict):
                try:
                    group = cls.model_validate(item, strict=False)
                    result.append(group)
                except Exception:
                    result.append(item)
            else:
                result.append(item)
        return result
    
    @field_validator('criteria_list', mode='before')
    @classmethod
    def deserialize_criteria_list(cls, v: Any) -> Any:
        # Logic adapted for local CorelatedCriteria
        if not v or not isinstance(v, list):
            return v
        
        # Helper window normalizer (same as before)
        def normalize_window(window_dict: dict) -> dict:
            if not isinstance(window_dict, dict): return window_dict
            normalized = {}
            if 'UseEventEnd' in window_dict: normalized['useEventEnd'] = window_dict['UseEventEnd']
            elif 'useEventEnd' in window_dict: normalized['useEventEnd'] = window_dict['useEventEnd']
            if 'UseIndexEnd' in window_dict: normalized['useIndexEnd'] = window_dict['UseIndexEnd']
            elif 'useIndexEnd' in window_dict: normalized['useIndexEnd'] = window_dict['useIndexEnd']
            if 'useEventEnd' in normalized: normalized['useEventEnd'] = normalized['useEventEnd']
            if 'useIndexEnd' in normalized: normalized['useIndexEnd'] = normalized['useIndexEnd']
            
            if 'Start' in window_dict:
                start = window_dict['Start']
                if isinstance(start, dict):
                    coeff = start.get('Coeff') if 'Coeff' in start else start.get('coeff', 0)
                    days = start.get('Days') if 'Days' in start else start.get('days')
                    normalized['start'] = {'coeff': coeff, 'days': days}
                else: normalized['start'] = start
            if 'End' in window_dict:
                end = window_dict['End']
                if isinstance(end, dict):
                    coeff = end.get('Coeff') if 'Coeff' in end else end.get('coeff', 0)
                    days = end.get('Days') if 'Days' in end else end.get('days')
                    normalized['end'] = {'coeff': coeff, 'days': days}
                else: normalized['end'] = end
            
            if 'coeff' not in normalized and 'start' in normalized:
                if isinstance(normalized['start'], dict) and 'coeff' in normalized['start']:
                    normalized['coeff'] = normalized['start']['coeff']
                else: normalized['coeff'] = 0
            elif 'coeff' not in normalized: normalized['coeff'] = 0
            if 'useEventEnd' not in normalized: normalized['useEventEnd'] = False
            return normalized

        deserialized = []
        for item in v:
            if not isinstance(item, dict):
                deserialized.append(item)
                continue
            
            item_copy = dict(item)
            if 'StartWindow' in item_copy: item_copy['StartWindow'] = normalize_window(item_copy['StartWindow'])
            elif 'startWindow' in item_copy:
                item_copy['StartWindow'] = normalize_window(item_copy['startWindow'])
                item_copy.pop('startWindow', None)
            if 'EndWindow' in item_copy: item_copy['EndWindow'] = normalize_window(item_copy['EndWindow'])
            elif 'endWindow' in item_copy:
                item_copy['EndWindow'] = normalize_window(item_copy['endWindow'])
                item_copy.pop('endWindow', None)

            # Polymorphic handling for Criteria field
            if 'Criteria' in item_copy or 'criteria' in item_copy:
                if 'Criteria' in item_copy: item_copy['criteria'] = item_copy.pop('Criteria')
                # Inner criteria deserialization
                if isinstance(item_copy.get('criteria'), dict):
                    c_dict = item_copy['criteria']
                    c_type = next(iter(c_dict.keys()), None)
                    if c_type and c_type in NAMES_TO_CLASSES:
                        try:
                            c_data = dict(c_dict[c_type])
                            # PascalCase defaults
                            if c_type == 'Measurement' and 'MeasurementTypeExclude' not in c_data and 'measurementTypeExclude' not in c_data:
                                c_data['MeasurementTypeExclude'] = False
                            if c_type == 'Observation' and 'ObservationTypeExclude' not in c_data and 'observationTypeExclude' not in c_data:
                                c_data['ObservationTypeExclude'] = False
                            if c_type == 'ConditionOccurrence' and 'ConditionTypeExclude' not in c_data and 'conditionTypeExclude' not in c_data:
                                c_data['ConditionTypeExclude'] = False
                            if 'First' not in c_data and 'first' not in c_data:
                                c_data['First'] = False
                            
                            c_obj = NAMES_TO_CLASSES[c_type].model_validate(c_data, strict=False)
                            item_copy['criteria'] = c_obj
                        except: pass
            
                if 'Occurrence' in item_copy:
                    occ = item_copy.pop('Occurrence')
                    item_copy['occurrence'] = Occurrence.model_validate(occ) if isinstance(occ, dict) else occ
                elif 'occurrence' not in item_copy:
                    item_copy['occurrence'] = Occurrence(type=Occurrence._AT_LEAST, count=1, is_distinct=False)

                try:
                    deserialized.append(CorelatedCriteria.model_validate(item_copy))
                except: deserialized.append(item)
            
            elif any(k in item_copy for k in ['StartWindow', 'EndWindow', 'RestrictVisit', 'IgnoreObservationPeriod']):
                # Implicit CorelatedCriteria
                c_type = next((k for k in item_copy.keys() if k not in ['StartWindow', 'EndWindow', 'RestrictVisit', 'IgnoreObservationPeriod', 'Occurrence', 'criteria']), None)
                if c_type and c_type in NAMES_TO_CLASSES:
                    c_data = item_copy[c_type]
                    # Explicitly deserialize inner criteria to avoid Pydantic union ambiguity
                    try:
                        # PascalCase defaults for specific types
                        if c_type == 'Measurement' and 'MeasurementTypeExclude' not in c_data and 'measurementTypeExclude' not in c_data:
                            c_data['MeasurementTypeExclude'] = False
                        if c_type == 'Observation' and 'ObservationTypeExclude' not in c_data and 'observationTypeExclude' not in c_data:
                            c_data['ObservationTypeExclude'] = False
                        if c_type == 'ConditionOccurrence' and 'ConditionTypeExclude' not in c_data and 'conditionTypeExclude' not in c_data:
                            c_data['ConditionTypeExclude'] = False
                        if 'First' not in c_data and 'first' not in c_data:
                            c_data['First'] = False
                            
                        c_obj = NAMES_TO_CLASSES[c_type].model_validate(c_data, strict=False)
                        
                        corelated_dict = {
                            'criteria': c_obj,
                            'Occurrence': item_copy.get('Occurrence', {'Type': Occurrence._AT_LEAST, 'Count': 1, 'IsDistinct': False})
                        }
                        for f in ['StartWindow', 'EndWindow', 'RestrictVisit', 'IgnoreObservationPeriod']:
                            if f in item_copy: corelated_dict[f] = item_copy[f]
                        
                        deserialized.append(CorelatedCriteria.model_validate(corelated_dict))
                    except: deserialized.append(item)
                else: deserialized.append(item)
            
            else:
                # Simple polymorphic wrapped in corelated
                c_type = next(iter(item_copy.keys()), None)
                if c_type and c_type in NAMES_TO_CLASSES:
                    try:
                        c_data = item_copy[c_type]
                        # PascalCase defaults
                        if c_type == 'Measurement' and 'MeasurementTypeExclude' not in c_data and 'measurementTypeExclude' not in c_data:
                            c_data['MeasurementTypeExclude'] = False
                        if c_type == 'Observation' and 'ObservationTypeExclude' not in c_data and 'observationTypeExclude' not in c_data:
                            c_data['ObservationTypeExclude'] = False
                        if c_type == 'ConditionOccurrence' and 'ConditionTypeExclude' not in c_data and 'conditionTypeExclude' not in c_data:
                            c_data['ConditionTypeExclude'] = False
                        if 'First' not in c_data and 'first' not in c_data:
                            c_data['First'] = False

                        c_obj = NAMES_TO_CLASSES[c_type].model_validate(c_data, strict=False)
                        corelated_dict = {'criteria': c_obj}
                        deserialized.append(CorelatedCriteria.model_validate(corelated_dict))
                    except: deserialized.append(item)
                else: deserialized.append(item)

        return deserialized


# Define CriteriaType Union for strict typing
CriteriaType = Union[
    ConditionOccurrence, DrugExposure, ProcedureOccurrence,
    VisitOccurrence, Observation, Measurement, DeviceExposure,
    Specimen, Death, VisitDetail, ObservationPeriod,
    PayerPlanPeriod, LocationRegion, ConditionEra,
    DrugEra, DoseEra
]

# Map for dynamic lookup
NAMES_TO_CLASSES = {
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


class PrimaryCriteria(BaseModel):
    """Represents the primary criteria for cohort definition.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.PrimaryCriteria
    """
    criteria_list: Optional[List[CriteriaType]] = Field(
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
        validation_alias=AliasChoices("PrimaryLimit", "PrimaryCriteriaLimit", "primaryCriteriaLimit", "primaryLimit", "PrimaryLimit"),
        serialization_alias="PrimaryCriteriaLimit"
    )

    model_config = ConfigDict(populate_by_name=True)
    
    @field_validator('criteria_list', mode='before')
    @classmethod
    def deserialize_criteria_list(cls, v: Any) -> Any:
        if not v or not isinstance(v, list):
            return v
        
        deserialized = []
        for item in v:
            if not isinstance(item, dict):
                deserialized.append(item)
                continue
            
            # Find the type key (e.g. "ConditionOccurrence" or "conditionOccurrence")
            c_type_raw = next(iter(item.keys()), None)
            
            # Case-insensitive lookup
            c_type = None
            if c_type_raw:
                # Direct match
                if c_type_raw in NAMES_TO_CLASSES:
                    c_type = c_type_raw
                # Case-insensitive match
                else:
                    for k in NAMES_TO_CLASSES:
                        if k.lower() == c_type_raw.lower():
                            c_type = k
                            break
            
            if c_type:
                try:
                    c_data = dict(item[c_type_raw])
                    if c_type == 'Measurement' and 'MeasurementTypeExclude' not in c_data: c_data['MeasurementTypeExclude'] = False
                    if c_type == 'Observation' and 'ObservationTypeExclude' not in c_data: c_data['ObservationTypeExclude'] = False
                    if c_type == 'ConditionOccurrence' and 'ConditionTypeExclude' not in c_data: c_data['ConditionTypeExclude'] = False
                    if 'First' not in c_data: c_data['First'] = False
                    
                    obj = NAMES_TO_CLASSES[c_type].model_validate(c_data, strict=False)
                    deserialized.append(obj)
                except: deserialized.append(item)
            else:
                deserialized.append(item)
        return deserialized
