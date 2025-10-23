"""
Criteria classes for cohort definition.

This module contains classes for defining various types of criteria used in cohort expressions.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Any, ClassVar
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from ..vocabulary.concept import Concept
from .core import (
    DateAdjustment, CriteriaGroup, DateRange, NumericRange, ConceptSetSelection,
    TextFilter, Window, WindowedCriteria
)


class CriteriaColumn(str, Enum):
    """Represents a criteria column.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CriteriaColumn
    """
    AGE = "age"
    GENDER = "gender"
    RACE = "race"
    ETHNICITY = "ethnicity"
    DOMAIN_CONCEPT = "domain_concept"


class Occurrence(BaseModel):
    """Represents occurrence settings for criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Occurrence
    """
    # Constants
    AT_MOST: ClassVar[int] = 0
    AT_LEAST: ClassVar[int] = 1
    EXACTLY: ClassVar[int] = 2
    
    at_most: int = Field(alias="AT_MOST")
    at_least: int = Field(alias="AT_LEAST")
    count_column: Optional[CriteriaColumn] = Field(default=None, alias="countColumn")
    is_distinct: bool = Field(alias="isDistinct")
    type: int
    exactly: int = Field(alias="EXACTLY")
    count: int

    model_config = ConfigDict(populate_by_name=True)


class CorelatedCriteria(WindowedCriteria):
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
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: Optional[bool] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    condition_type: Optional[List[Concept]] = Field(default=None, alias="conditionType")
    condition_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="conditionTypeCS")
    condition_type_exclude: Optional[bool] = Field(default=False, alias="conditionTypeExclude")
    stop_reason: Optional[TextFilter] = Field(default=None, alias="stopReason")
    condition_source_concept: Optional[int] = Field(default=None, alias="conditionSourceConcept")
    age: Optional[NumericRange] = None
    gender: Optional[List[Concept]] = None
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="providerSpecialty")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="providerSpecialtyCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="visitType")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="visitTypeCS")
    condition_status: Optional[List[Concept]] = Field(default=None, alias="conditionStatus")
    condition_status_cs: Optional[ConceptSetSelection] = Field(default=None, alias="conditionStatusCS")
    date_adjustment: Optional[DateAdjustment] = Field(default=None, alias="dateAdjustment")

    model_config = ConfigDict(populate_by_name=True)


class DrugExposure(Criteria):
    """Drug exposure criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DrugExposure
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    stop_reason: Optional[TextFilter] = Field(default=None, alias="stopReason")
    drug_source_concept: Optional[int] = Field(default=None, alias="drugSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    drug_type: Optional[List[Concept]] = Field(default=None, alias="drugType")
    drug_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="drugTypeCS")
    drug_type_exclude: bool = Field(alias="drugTypeExclude")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="providerSpecialtyCS")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="visitTypeCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="visitType")
    route_concept: Optional[List[Concept]] = Field(default=None, alias="routeConcept")
    route_concept_cs: Optional[ConceptSetSelection] = Field(default=None, alias="routeConceptCS")
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: bool
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="providerSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class ProcedureOccurrence(Criteria):
    """Procedure occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ProcedureOccurrence
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    procedure_source_concept: Optional[int] = Field(default=None, alias="procedureSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    procedure_type: Optional[List[Concept]] = Field(default=None, alias="procedureType")
    procedure_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="procedureTypeCS")
    procedure_type_exclude: bool = Field(alias="procedureTypeExclude")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="providerSpecialtyCS")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="visitTypeCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="visitType")
    modifier: Optional[List[Concept]] = None
    modifier_cs: Optional[ConceptSetSelection] = Field(default=None, alias="modifierCS")
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: bool
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="providerSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class VisitOccurrence(Criteria):
    """Visit occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.VisitOccurrence
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="visitType")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="visitTypeCS")
    visit_type_exclude: bool = Field(alias="visitTypeExclude")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="providerSpecialtyCS")
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="providerSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class Observation(Criteria):
    """Observation criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Observation
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    observation_source_concept: Optional[int] = Field(default=None, alias="observationSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    observation_type: Optional[List[Concept]] = Field(default=None, alias="observationType")
    observation_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="observationTypeCS")
    observation_type_exclude: bool = Field(alias="observationTypeExclude")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="providerSpecialtyCS")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="visitTypeCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="visitType")
    value_as_string: Optional[TextFilter] = Field(default=None, alias="valueAsString")
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: bool
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="providerSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class Measurement(Criteria):
    """Measurement criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Measurement
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    measurement_source_concept: Optional[int] = Field(default=None, alias="measurementSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    measurement_type: Optional[List[Concept]] = Field(default=None, alias="measurementType")
    measurement_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="measurementTypeCS")
    measurement_type_exclude: bool = Field(alias="measurementTypeExclude")
    operator: Optional[List[Concept]] = None
    operator_cs: Optional[ConceptSetSelection] = Field(default=None, alias="operatorCS")
    value_as_number: Optional[NumericRange] = Field(default=None, alias="valueAsNumber")
    value_as_string: Optional[TextFilter] = Field(default=None, alias="valueAsString")
    unit: Optional[List[Concept]] = None
    unit_cs: Optional[ConceptSetSelection] = Field(default=None, alias="unitCS")
    range_low: Optional[NumericRange] = Field(default=None, alias="rangeLow")
    range_high: Optional[NumericRange] = Field(default=None, alias="rangeHigh")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="providerSpecialtyCS")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="visitTypeCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="visitType")
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: bool
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="providerSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class DeviceExposure(Criteria):
    """Device exposure criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DeviceExposure
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    device_source_concept: Optional[int] = Field(default=None, alias="deviceSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    device_type: Optional[List[Concept]] = Field(default=None, alias="deviceType")
    device_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="deviceTypeCS")
    device_type_exclude: bool = Field(alias="deviceTypeExclude")
    unique_device_id: Optional[TextFilter] = Field(default=None, alias="uniqueDeviceId")
    quantity: Optional[NumericRange] = None
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="providerSpecialtyCS")
    visit_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="visitTypeCS")
    visit_type: Optional[List[Concept]] = Field(default=None, alias="visitType")
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: bool
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="providerSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class Specimen(Criteria):
    """Specimen criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Specimen
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    specimen_source_concept: Optional[int] = Field(default=None, alias="specimenSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    specimen_type: Optional[List[Concept]] = Field(default=None, alias="specimenType")
    specimen_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="specimenTypeCS")
    specimen_type_exclude: bool = Field(alias="specimenTypeExclude")
    unit: Optional[List[Concept]] = None
    unit_cs: Optional[ConceptSetSelection] = Field(default=None, alias="unitCS")
    anatomic_site: Optional[List[Concept]] = Field(default=None, alias="anatomicSite")
    anatomic_site_cs: Optional[ConceptSetSelection] = Field(default=None, alias="anatomicSiteCS")
    disease_status: Optional[List[Concept]] = Field(default=None, alias="diseaseStatus")
    disease_status_cs: Optional[ConceptSetSelection] = Field(default=None, alias="diseaseStatusCS")
    quantity: Optional[NumericRange] = None
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: bool
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class Death(Criteria):
    """Death criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.Death
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    death_source_concept: Optional[int] = Field(default=None, alias="deathSourceConcept")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    death_type: Optional[List[Concept]] = Field(default=None, alias="deathType")
    death_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="deathTypeCS")
    death_type_exclude: bool = Field(alias="deathTypeExclude")
    cause_source_concept: Optional[int] = Field(default=None, alias="causeSourceConcept")
    cause_source_concept_cs: Optional[ConceptSetSelection] = Field(default=None, alias="causeSourceConceptCS")
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: bool
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class VisitDetail(Criteria):
    """Visit detail criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.VisitDetail
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    visit_detail_type: Optional[List[Concept]] = Field(default=None, alias="visitDetailType")
    visit_detail_type_cs: Optional[ConceptSetSelection] = Field(default=None, alias="visitDetailTypeCS")
    visit_detail_type_exclude: bool = Field(alias="visitDetailTypeExclude")
    provider_specialty_cs: Optional[ConceptSetSelection] = Field(default=None, alias="providerSpecialtyCS")
    provider_specialty: Optional[List[Concept]] = Field(default=None, alias="providerSpecialty")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class ObservationPeriod(Criteria):
    """Observation period criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ObservationPeriod
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class PayerPlanPeriod(Criteria):
    """Payer plan period criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.PayerPlanPeriod
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    payer_source_concept: Optional[int] = Field(default=None, alias="payerSourceConcept")
    payer_source_concept_cs: Optional[ConceptSetSelection] = Field(default=None, alias="payerSourceConceptCS")
    plan_source_concept: Optional[int] = Field(default=None, alias="planSourceConcept")
    plan_source_concept_cs: Optional[ConceptSetSelection] = Field(default=None, alias="planSourceConceptCS")
    sponsor_source_concept: Optional[int] = Field(default=None, alias="sponsorSourceConcept")
    sponsor_source_concept_cs: Optional[ConceptSetSelection] = Field(default=None, alias="sponsorSourceConceptCS")
    stop_reason_source_concept: Optional[int] = Field(default=None, alias="stopReasonSourceConcept")
    stop_reason_source_concept_cs: Optional[ConceptSetSelection] = Field(default=None, alias="stopReasonSourceConceptCS")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


class LocationRegion(Criteria):
    """Location region criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.LocationRegion
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# ERA CRITERIA CLASSES
# =============================================================================

class ConditionEra(Criteria):
    """Condition era criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ConditionEra
    """
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: Optional[bool] = None
    era_start_date: Optional[DateRange] = Field(default=None, alias="eraStartDate")
    era_end_date: Optional[DateRange] = Field(default=None, alias="eraEndDate")
    occurrence_count: Optional[NumericRange] = Field(default=None, alias="occurrenceCount")
    era_length: Optional[NumericRange] = Field(default=None, alias="eraLength")
    age_at_start: Optional[NumericRange] = Field(default=None, alias="ageAtStart")
    age_at_end: Optional[NumericRange] = Field(default=None, alias="ageAtEnd")
    gender: Optional[List[Concept]] = None
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    date_adjustment: Optional[DateAdjustment] = Field(default=None, alias="dateAdjustment")

    model_config = ConfigDict(populate_by_name=True)


class DrugEra(Criteria):
    """Drug era criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DrugEra
    """
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: Optional[bool] = None
    era_start_date: Optional[DateRange] = Field(default=None, alias="eraStartDate")
    era_end_date: Optional[DateRange] = Field(default=None, alias="eraEndDate")
    occurrence_count: Optional[NumericRange] = Field(default=None, alias="occurrenceCount")
    gap_days: Optional[NumericRange] = Field(default=None, alias="gapDays")
    era_length: Optional[NumericRange] = Field(default=None, alias="eraLength")
    age_at_start: Optional[NumericRange] = Field(default=None, alias="ageAtStart")
    age_at_end: Optional[NumericRange] = Field(default=None, alias="ageAtEnd")
    gender: Optional[List[Concept]] = None
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    date_adjustment: Optional[DateAdjustment] = Field(default=None, alias="dateAdjustment")

    model_config = ConfigDict(populate_by_name=True)


class DoseEra(Criteria):
    """Dose era criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.DoseEra
    """
    gender: Optional[List[Concept]] = None
    occurrence_end_date: Optional[DateRange] = Field(default=None, alias="occurrenceEndDate")
    gender_cs: Optional[ConceptSetSelection] = Field(default=None, alias="genderCS")
    era_length: Optional[NumericRange] = Field(default=None, alias="eraLength")
    dose_value: Optional[NumericRange] = Field(default=None, alias="doseValue")
    unit: Optional[List[Concept]] = None
    unit_cs: Optional[ConceptSetSelection] = Field(default=None, alias="unitCS")
    codeset_id: Optional[int] = Field(default=None, alias="codesetId")
    first: bool
    age: Optional[NumericRange] = None
    occurrence_start_date: Optional[DateRange] = Field(default=None, alias="occurrenceStartDate")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# GEOGRAPHIC CRITERIA
# =============================================================================

class GeoCriteria(Criteria):
    """Base class for geographic criteria.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.GeoCriteria
    """
    pass
