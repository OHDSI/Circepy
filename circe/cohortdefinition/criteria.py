"""
Criteria classes for cohort definition.

This module contains classes for defining various types of criteria used in cohort expressions.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Any, ClassVar
from pydantic import BaseModel, Field, ConfigDict, model_serializer, AliasChoices
from enum import Enum
from ..vocabulary.concept import Concept
from .core import (
    DateAdjustment, CriteriaGroup, DateRange, NumericRange, ConceptSetSelection,
    TextFilter, Window, WindowedCriteria, Period
)


class CriteriaColumn(str, Enum):
    """Represents a criteria column.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.builders.CriteriaColumn
    """
    DAYS_SUPPLY = "days_supply"
    DOMAIN_CONCEPT = "domain_concept"
    DOMAIN_SOURCE_CONCEPT = "domain_source_concept"
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
    AGE = "age"
    GENDER = "gender"
    RACE = "race"
    ETHNICITY = "ethnicity"


class Occurrence(BaseModel):
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


class DemographicCriteria(BaseModel):
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


class Criteria(BaseModel):
    """Represents a criteria with date adjustment and correlated criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Criteria
    """
    date_adjustment: Optional[DateAdjustment] = Field(
        default=None,
        validation_alias=AliasChoices("DateAdjustment", "dateAdjustment"),
        serialization_alias="DateAdjustment"
    )
    correlated_criteria: Optional[CriteriaGroup] = Field(
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


class InclusionRule(BaseModel):
    """Represents an inclusion rule for cohort definition.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.InclusionRule
    """
    expression: Optional[CriteriaGroup] = None
    description: Optional[str] = None
    name: Optional[str] = None


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
    gender: Optional[List[Concept]] = None
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
    gender: Optional[List[Concept]] = None
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
    first: bool = Field(
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


class ProcedureOccurrence(Criteria):
    """Procedure occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ProcedureOccurrence
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="OccurrenceEndDate")
    procedure_source_concept: Optional[int] = Field(default=None, alias="ProcedureSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    procedure_type: Optional[List[Concept]] = Field(default=None, alias="ProcedureType")
    procedure_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ProcedureTypeCS")
    procedure_type_exclude: bool = Field(default=False, alias="ProcedureTypeExclude")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ProviderSpecialtyCS")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="VisitTypeCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="VisitType")
    modifier: Optional[List[Concept]] = None
    modifier_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ModifierCS")
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: bool = Field(
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="ProviderSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="OccurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class VisitOccurrence(Criteria):
    """Visit occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.VisitOccurrence
    """
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: Optional[bool] = Field(default=None, alias="First")
    gender: Optional[List[Concept]] = None
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
    gender: Optional[List[Concept]] = None
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
    first: bool = Field(
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
    gender: Optional[List[Concept]] = None
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
    first: bool = Field(
        default=False,
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
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="OccurrenceEndDate")
    device_source_concept: Optional[int] = Field(default=None, alias="DeviceSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    device_type: Optional[List[Concept]] = Field(default=None, alias="DeviceType")
    device_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="DeviceTypeCS")
    device_type_exclude: bool = Field(alias="DeviceTypeExclude")
    unique_device_id: Optional[TextFilter] = Field(default=None, alias="UniqueDeviceId")
    quantity: Optional[NumericRange] = None
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ProviderSpecialtyCS")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="VisitTypeCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="VisitType")
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: bool = Field(
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="ProviderSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="OccurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class Specimen(Criteria):
    """Specimen criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Specimen
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="OccurrenceEndDate")
    specimen_source_concept: Optional[int] = Field(default=None, alias="SpecimenSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    specimen_type: Optional[List[Concept]] = Field(default=None, alias="SpecimenType")
    specimen_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="SpecimenTypeCS")
    specimen_type_exclude: bool = Field(alias="SpecimenTypeExclude")
    unit: Optional[List[Concept]] = None
    unit_cs: Optional[ConceptSetSelection] = Field(default=None, alias="UnitCS")
    anatomic_site: Optional[List[Concept]] = Field(default=None, alias="AnatomicSite")
    anatomic_site_cs: Optional[ConceptSetSelection] = Field(default=None, alias="AnatomicSiteCS")
    disease_status: Optional[List[Concept]] = Field(default=None, alias="DiseaseStatus")
    disease_status_cs: Optional[ConceptSetSelection] = Field(default=None, alias="DiseaseStatusCS")
    quantity: Optional[NumericRange] = None
    codeset_id: Optional[int] = Field(default=None, alias="CodesetId")
    first: bool = Field(
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
    gender: Optional[List[Concept]] = None
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
    first: bool = Field(
        validation_alias=AliasChoices("First", "first"),
        serialization_alias="First"
    )
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
    visit_detail_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="VisitDetailTypeCS")
    visit_detail_type_exclude: bool = Field(default=False, alias="VisitDetailTypeExclude")
    visit_detail_source_concept: Optional[int] = Field(default=None, alias="VisitDetailSourceConcept")
    visit_detail_length: Optional[NumericRange] = Field(default=None, alias="VisitDetailLength")
    age: Optional[NumericRange] = Field(default=None, alias="Age")
    gender: Optional[List[Concept]] = None
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="GenderCS")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="ProviderSpecialtyCS")
    place_of_service_cs: Optional[ConceptSetSelection] = Field(default=None, alias="PlaceOfServiceCS")
    place_of_service_location: Optional[int] = Field(default=None, alias="PlaceOfServiceLocation")

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
    gender: Optional[List[Concept]] = Field(default=None, alias="Gender")
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
    gender: Optional[List[Concept]] = None
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
    gender: Optional[List[Concept]] = None
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
    gender: Optional[List[Concept]] = Field(default=None, alias="Gender")
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
