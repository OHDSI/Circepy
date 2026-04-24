"""
Domain query functions for CohortComposer.

Each function creates a query object that specifies which concepts to extract
from which OMOP CDM domain table. These are used as entry events or within
criteria for attrition rules.

Modeled after OHDSI/Capr R package query functions.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Query:
    """
    Base query object representing a domain-specific event search.

    Attributes:
        domain: The OMOP CDM domain (e.g., 'ConditionOccurrence')
        concept_set_id: ID of the concept set to search for
        first_occurrence: If True, only use the first occurrence per person
        criteria_options: Additional domain-specific filter options
    """

    domain: str
    concept_set_id: Optional[int] = None
    first_occurrence: bool = False
    criteria_options: dict = field(default_factory=dict)

    def first(self) -> "Query":
        """Return a copy with first_occurrence=True."""
        return Query(
            domain=self.domain,
            concept_set_id=self.concept_set_id,
            first_occurrence=True,
            criteria_options=self.criteria_options.copy(),
        )


def condition_occurrence(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    condition_status: Optional[list[int]] = None,
    condition_type: Optional[list[int]] = None,
    visit_type: Optional[list[int]] = None,
    provider_specialty: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for condition occurrences.

    Args:
        concept_set_id: ID of the concept set defining the conditions
        first_occurrence: If True, only use first occurrence per person
        age: Tuple of (min, max) age at occurrence, or single value for minimum
        gender: List of gender concept IDs
        condition_status: List of condition status concept IDs
        condition_type: List of condition type concept IDs
        visit_type: List of visit type concept IDs
        provider_specialty: List of provider specialty concept IDs

    Returns:
        Query object for condition occurrences
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if condition_status is not None:
        options["condition_status"] = condition_status
    if condition_type is not None:
        options["condition_type"] = condition_type
    if visit_type is not None:
        options["visit_type"] = visit_type
    if provider_specialty is not None:
        options["provider_specialty"] = provider_specialty
    options.update(kwargs)

    return Query(
        domain="ConditionOccurrence",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def condition_era(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    era_length: Optional[tuple] = None,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for condition eras.

    Args:
        concept_set_id: ID of the concept set defining the conditions
        first_occurrence: If True, only use first era per person
        era_length: Tuple of (min, max) era length in days
        age: Tuple of (min, max) age at era start
        gender: List of gender concept IDs

    Returns:
        Query object for condition eras
    """
    options = {}
    if era_length is not None:
        options["era_length"] = era_length
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    options.update(kwargs)

    return Query(
        domain="ConditionEra",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def drug_exposure(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    drug_type: Optional[list[int]] = None,
    route: Optional[list[int]] = None,
    dose_unit: Optional[list[int]] = None,
    days_supply: Optional[tuple] = None,
    quantity: Optional[tuple] = None,
    refills: Optional[tuple] = None,
    visit_type: Optional[list[int]] = None,
    provider_specialty: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for drug exposures.

    Args:
        concept_set_id: ID of the concept set defining the drugs
        first_occurrence: If True, only use first exposure per person
        age: Tuple of (min, max) age at exposure
        gender: List of gender concept IDs
        drug_type: List of drug type concept IDs
        route: List of route concept IDs
        dose_unit: List of dose unit concept IDs
        days_supply: Tuple of (min, max) days supply
        quantity: Tuple of (min, max) quantity
        refills: Tuple of (min, max) refills
        visit_type: List of visit type concept IDs
        provider_specialty: List of provider specialty concept IDs

    Returns:
        Query object for drug exposures
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if drug_type is not None:
        options["drug_type"] = drug_type
    if route is not None:
        options["route"] = route
    if dose_unit is not None:
        options["dose_unit"] = dose_unit
    if days_supply is not None:
        options["days_supply"] = days_supply
    if quantity is not None:
        options["quantity"] = quantity
    if refills is not None:
        options["refills"] = refills
    if visit_type is not None:
        options["visit_type"] = visit_type
    if provider_specialty is not None:
        options["provider_specialty"] = provider_specialty
    options.update(kwargs)

    return Query(
        domain="DrugExposure",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def drug_era(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    era_length: Optional[tuple] = None,
    gap_days: Optional[tuple] = None,
    occurrence_count: Optional[tuple] = None,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for drug eras.

    Args:
        concept_set_id: ID of the concept set defining the drugs
        first_occurrence: If True, only use first era per person
        era_length: Tuple of (min, max) era length in days
        gap_days: Tuple of (min, max) gap days
        occurrence_count: Tuple of (min, max) occurrence count within era
        age: Tuple of (min, max) age at era start
        gender: List of gender concept IDs

    Returns:
        Query object for drug eras
    """
    options = {}
    if era_length is not None:
        options["era_length"] = era_length
    if gap_days is not None:
        options["gap_days"] = gap_days
    if occurrence_count is not None:
        options["occurrence_count"] = occurrence_count
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    options.update(kwargs)

    return Query(
        domain="DrugEra",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def dose_era(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    era_length: Optional[tuple] = None,
    unit: Optional[list[int]] = None,
    dose_value: Optional[tuple] = None,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for dose eras.

    Args:
        concept_set_id: ID of the concept set defining the drugs
        first_occurrence: If True, only use first era per person
        era_length: Tuple of (min, max) era length in days
        unit: List of unit concept IDs
        dose_value: Tuple of (min, max) dose value
        age: Tuple of (min, max) age at era start
        gender: List of gender concept IDs

    Returns:
        Query object for dose eras
    """
    options = {}
    if era_length is not None:
        options["era_length"] = era_length
    if unit is not None:
        options["unit"] = unit
    if dose_value is not None:
        options["dose_value"] = dose_value
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    options.update(kwargs)

    return Query(
        domain="DoseEra",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def procedure(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    procedure_type: Optional[list[int]] = None,
    modifier: Optional[list[int]] = None,
    quantity: Optional[tuple] = None,
    visit_type: Optional[list[int]] = None,
    provider_specialty: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for procedure occurrences.

    Args:
        concept_set_id: ID of the concept set defining the procedures
        first_occurrence: If True, only use first procedure per person
        age: Tuple of (min, max) age at procedure
        gender: List of gender concept IDs
        procedure_type: List of procedure type concept IDs
        modifier: List of modifier concept IDs
        quantity: Tuple of (min, max) quantity
        visit_type: List of visit type concept IDs
        provider_specialty: List of provider specialty concept IDs

    Returns:
        Query object for procedure occurrences
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if procedure_type is not None:
        options["procedure_type"] = procedure_type
    if modifier is not None:
        options["modifier"] = modifier
    if quantity is not None:
        options["quantity"] = quantity
    if visit_type is not None:
        options["visit_type"] = visit_type
    if provider_specialty is not None:
        options["provider_specialty"] = provider_specialty
    options.update(kwargs)

    return Query(
        domain="ProcedureOccurrence",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def measurement(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    measurement_type: Optional[list[int]] = None,
    operator: Optional[list[int]] = None,
    value_as_number: Optional[tuple] = None,
    value_as_concept: Optional[list[int]] = None,
    unit: Optional[list[int]] = None,
    range_low: Optional[tuple] = None,
    range_high: Optional[tuple] = None,
    abnormal: Optional[bool] = None,
    visit_type: Optional[list[int]] = None,
    provider_specialty: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for measurements.

    Args:
        concept_set_id: ID of the concept set defining the measurements
        first_occurrence: If True, only use first measurement per person
        age: Tuple of (min, max) age at measurement
        gender: List of gender concept IDs
        measurement_type: List of measurement type concept IDs
        operator: List of operator concept IDs
        value_as_number: Tuple of (min, max) numeric value
        value_as_concept: List of value as concept IDs
        unit: List of unit concept IDs
        range_low: Tuple of (min, max) range low
        range_high: Tuple of (min, max) range high
        abnormal: If True, only include abnormal values
        visit_type: List of visit type concept IDs
        provider_specialty: List of provider specialty concept IDs

    Returns:
        Query object for measurements
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if measurement_type is not None:
        options["measurement_type"] = measurement_type
    if operator is not None:
        options["operator"] = operator
    if value_as_number is not None:
        options["value_as_number"] = value_as_number
    if value_as_concept is not None:
        options["value_as_concept"] = value_as_concept
    if unit is not None:
        options["unit"] = unit
    if range_low is not None:
        options["range_low"] = range_low
    if range_high is not None:
        options["range_high"] = range_high
    if abnormal is not None:
        options["abnormal"] = abnormal
    if visit_type is not None:
        options["visit_type"] = visit_type
    if provider_specialty is not None:
        options["provider_specialty"] = provider_specialty
    options.update(kwargs)

    return Query(
        domain="Measurement",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def observation(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    observation_type: Optional[list[int]] = None,
    value_as_number: Optional[tuple] = None,
    value_as_string: Optional[str] = None,
    value_as_concept: Optional[list[int]] = None,
    qualifier: Optional[list[int]] = None,
    unit: Optional[list[int]] = None,
    visit_type: Optional[list[int]] = None,
    provider_specialty: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for observations.

    Args:
        concept_set_id: ID of the concept set defining the observations
        first_occurrence: If True, only use first observation per person
        age: Tuple of (min, max) age at observation
        gender: List of gender concept IDs
        observation_type: List of observation type concept IDs
        value_as_number: Tuple of (min, max) numeric value
        value_as_string: String pattern to match
        value_as_concept: List of value as concept IDs
        qualifier: List of qualifier concept IDs
        unit: List of unit concept IDs
        visit_type: List of visit type concept IDs
        provider_specialty: List of provider specialty concept IDs

    Returns:
        Query object for observations
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if observation_type is not None:
        options["observation_type"] = observation_type
    if value_as_number is not None:
        options["value_as_number"] = value_as_number
    if value_as_string is not None:
        options["value_as_string"] = value_as_string
    if value_as_concept is not None:
        options["value_as_concept"] = value_as_concept
    if qualifier is not None:
        options["qualifier"] = qualifier
    if unit is not None:
        options["unit"] = unit
    if visit_type is not None:
        options["visit_type"] = visit_type
    if provider_specialty is not None:
        options["provider_specialty"] = provider_specialty
    options.update(kwargs)

    return Query(
        domain="Observation",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def visit(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    visit_type: Optional[list[int]] = None,
    visit_length: Optional[tuple] = None,
    place_of_service: Optional[list[int]] = None,
    provider_specialty: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for visit occurrences.

    Args:
        concept_set_id: ID of the concept set defining the visits
        first_occurrence: If True, only use first visit per person
        age: Tuple of (min, max) age at visit
        gender: List of gender concept IDs
        visit_type: List of visit type concept IDs
        visit_length: Tuple of (min, max) visit length in days
        place_of_service: List of place of service concept IDs
        provider_specialty: List of provider specialty concept IDs

    Returns:
        Query object for visit occurrences
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if visit_type is not None:
        options["visit_type"] = visit_type
    if visit_length is not None:
        options["visit_length"] = visit_length
    if place_of_service is not None:
        options["place_of_service"] = place_of_service
    if provider_specialty is not None:
        options["provider_specialty"] = provider_specialty
    options.update(kwargs)

    return Query(
        domain="VisitOccurrence",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def visit_detail(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    visit_detail_type: Optional[list[int]] = None,
    visit_detail_length: Optional[tuple] = None,
    place_of_service: Optional[list[int]] = None,
    provider_specialty: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for visit details.

    Args:
        concept_set_id: ID of the concept set defining the visit details
        first_occurrence: If True, only use first visit detail per person
        age: Tuple of (min, max) age at visit detail
        gender: List of gender concept IDs
        visit_detail_type: List of visit detail type concept IDs
        visit_detail_length: Tuple of (min, max) visit detail length in days
        place_of_service: List of place of service concept IDs
        provider_specialty: List of provider specialty concept IDs

    Returns:
        Query object for visit details
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if visit_detail_type is not None:
        options["visit_detail_type"] = visit_detail_type
    if visit_detail_length is not None:
        options["visit_detail_length"] = visit_detail_length
    if place_of_service is not None:
        options["place_of_service"] = place_of_service
    if provider_specialty is not None:
        options["provider_specialty"] = provider_specialty
    options.update(kwargs)

    return Query(
        domain="VisitDetail",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def device_exposure(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    device_type: Optional[list[int]] = None,
    unique_device_id: Optional[str] = None,
    quantity: Optional[tuple] = None,
    visit_type: Optional[list[int]] = None,
    provider_specialty: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for device exposures.

    Args:
        concept_set_id: ID of the concept set defining the devices
        first_occurrence: If True, only use first device exposure per person
        age: Tuple of (min, max) age at device exposure
        gender: List of gender concept IDs
        device_type: List of device type concept IDs
        unique_device_id: Device identifier pattern
        quantity: Tuple of (min, max) quantity
        visit_type: List of visit type concept IDs
        provider_specialty: List of provider specialty concept IDs

    Returns:
        Query object for device exposures
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if device_type is not None:
        options["device_type"] = device_type
    if unique_device_id is not None:
        options["unique_device_id"] = unique_device_id
    if quantity is not None:
        options["quantity"] = quantity
    if visit_type is not None:
        options["visit_type"] = visit_type
    if provider_specialty is not None:
        options["provider_specialty"] = provider_specialty
    options.update(kwargs)

    return Query(
        domain="DeviceExposure",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def specimen(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    specimen_type: Optional[list[int]] = None,
    anatomic_site: Optional[list[int]] = None,
    disease_status: Optional[list[int]] = None,
    unit: Optional[list[int]] = None,
    quantity: Optional[tuple] = None,
    **kwargs,
) -> Query:
    """
    Create a query for specimens.

    Args:
        concept_set_id: ID of the concept set defining the specimens
        first_occurrence: If True, only use first specimen per person
        age: Tuple of (min, max) age at specimen collection
        gender: List of gender concept IDs
        specimen_type: List of specimen type concept IDs
        anatomic_site: List of anatomic site concept IDs
        disease_status: List of disease status concept IDs
        unit: List of unit concept IDs
        quantity: Tuple of (min, max) quantity

    Returns:
        Query object for specimens
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if specimen_type is not None:
        options["specimen_type"] = specimen_type
    if anatomic_site is not None:
        options["anatomic_site"] = anatomic_site
    if disease_status is not None:
        options["disease_status"] = disease_status
    if unit is not None:
        options["unit"] = unit
    if quantity is not None:
        options["quantity"] = quantity
    options.update(kwargs)

    return Query(
        domain="Specimen",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def death(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    death_type: Optional[list[int]] = None,
    **kwargs,
) -> Query:
    """
    Create a query for death events.

    Args:
        concept_set_id: ID of the concept set defining the cause of death (optional)
        first_occurrence: If True, only use first death event per person
        age: Tuple of (min, max) age at death
        gender: List of gender concept IDs
        death_type: List of death type concept IDs

    Returns:
        Query object for death events
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if death_type is not None:
        options["death_type"] = death_type
    options.update(kwargs)

    return Query(
        domain="Death",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def observation_period(
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    period_type: Optional[list[int]] = None,
    period_length: Optional[tuple] = None,
    user_defined_period: Optional[tuple] = None,
    **kwargs,
) -> Query:
    """
    Create a query for observation periods.

    Args:
        first_occurrence: If True, only use first observation period per person
        age: Tuple of (min, max) age at period start
        gender: List of gender concept IDs
        period_type: List of period type concept IDs
        period_length: Tuple of (min, max) period length in days
        user_defined_period: Tuple of (start_date, end_date) to filter periods

    Returns:
        Query object for observation periods
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if period_type is not None:
        options["period_type"] = period_type
    if period_length is not None:
        options["period_length"] = period_length
    if user_defined_period is not None:
        options["user_defined_period"] = user_defined_period
    options.update(kwargs)

    return Query(
        domain="ObservationPeriod",
        concept_set_id=None,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def payer_plan_period(
    concept_set_id: Optional[int] = None,
    first_occurrence: bool = False,
    age: Optional[tuple] = None,
    gender: Optional[list[int]] = None,
    payer_concept: Optional[list[int]] = None,
    plan_concept: Optional[list[int]] = None,
    period_length: Optional[tuple] = None,
    **kwargs,
) -> Query:
    """
    Create a query for payer plan periods.

    Args:
        concept_set_id: ID of the concept set defining the payer/plan
        first_occurrence: If True, only use first payer plan period per person
        age: Tuple of (min, max) age at period start
        gender: List of gender concept IDs
        payer_concept: List of payer concept IDs
        plan_concept: List of plan concept IDs
        period_length: Tuple of (min, max) period length in days

    Returns:
        Query object for payer plan periods
    """
    options = {}
    if age is not None:
        options["age"] = age
    if gender is not None:
        options["gender"] = gender
    if payer_concept is not None:
        options["payer_concept"] = payer_concept
    if plan_concept is not None:
        options["plan_concept"] = plan_concept
    if period_length is not None:
        options["period_length"] = period_length
    options.update(kwargs)

    return Query(
        domain="PayerPlanPeriod",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=options,
    )


def location_region(concept_set_id: Optional[int] = None, first_occurrence: bool = False, **kwargs) -> Query:
    """
    Create a query for location regions.

    Args:
        concept_set_id: ID of the concept set defining the regions
        first_occurrence: If True, only use first location per person

    Returns:
        Query object for location regions
    """
    return Query(
        domain="LocationRegion",
        concept_set_id=concept_set_id,
        first_occurrence=first_occurrence,
        criteria_options=kwargs,
    )
