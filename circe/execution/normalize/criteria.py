from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from typing import Optional, Tuple

from ...cohortdefinition.criteria import (
    ConditionOccurrence,
    ConditionEra,
    Criteria,
    Death,
    DeviceExposure,
    DoseEra,
    DrugExposure,
    DrugEra,
    Measurement,
    Observation,
    ObservationPeriod,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    LocationRegion,
    VisitDetail,
    VisitOccurrence,
)
from ...vocabulary.concept import Concept
from .._dataclass import frozen_slots_dataclass
from ..errors import UnsupportedCriterionError
from .windows import (
    NormalizedDateRange,
    NormalizedNumericRange,
    normalize_date_range,
    normalize_numeric_range,
)

if TYPE_CHECKING:
    from .groups import NormalizedCriteriaGroup


@frozen_slots_dataclass
class NormalizedPersonFilters:
    age: NormalizedNumericRange | None = None
    gender_concept_ids: Tuple[int, ...] = ()
    gender_codeset_id: int | None = None
    race_concept_ids: Tuple[int, ...] = ()
    race_codeset_id: int | None = None
    ethnicity_concept_ids: Tuple[int, ...] = ()
    ethnicity_codeset_id: int | None = None


@frozen_slots_dataclass
class NormalizedCriterion:
    raw_criteria: Criteria
    criterion_type: str
    domain: str
    source_table: str
    event_id_column: str
    start_date_column: str
    end_date_column: str
    concept_column: str | None
    source_concept_column: str | None
    visit_occurrence_column: str | None
    codeset_id: int | None
    first: bool
    occurrence_start_date: NormalizedDateRange | None
    occurrence_end_date: NormalizedDateRange | None
    person_filters: NormalizedPersonFilters
    correlated_criteria: "NormalizedCriteriaGroup | None" = None


def _concept_ids(values: Optional[list[Concept]]) -> Tuple[int, ...]:
    if not values:
        return ()
    output: list[int] = []
    for concept in values:
        if concept is None or concept.concept_id is None:
            continue
        cid = int(concept.concept_id)
        if cid not in output:
            output.append(cid)
    return tuple(output)


def _person_filters_from_criterion(criteria: Criteria) -> NormalizedPersonFilters:
    return NormalizedPersonFilters(
        age=normalize_numeric_range(getattr(criteria, "age", None)),
        gender_concept_ids=_concept_ids(getattr(criteria, "gender", None)),
        gender_codeset_id=(
            int(criteria.gender_cs.codeset_id)
            if getattr(criteria, "gender_cs", None)
            and criteria.gender_cs.codeset_id is not None
            else None
        ),
        race_concept_ids=_concept_ids(getattr(criteria, "race", None)),
        race_codeset_id=(
            int(criteria.race_cs.codeset_id)
            if getattr(criteria, "race_cs", None)
            and criteria.race_cs.codeset_id is not None
            else None
        ),
        ethnicity_concept_ids=_concept_ids(getattr(criteria, "ethnicity", None)),
        ethnicity_codeset_id=(
            int(criteria.ethnicity_cs.codeset_id)
            if getattr(criteria, "ethnicity_cs", None)
            and criteria.ethnicity_cs.codeset_id is not None
            else None
        ),
    )


def _build_normalized_criterion(
    *,
    criteria: Criteria,
    criterion_type: str,
    domain: str,
    source_table: str,
    event_id_column: str,
    start_date_column: str,
    end_date_column: str,
    concept_column: str | None,
    source_concept_column: str | None,
    visit_occurrence_column: str | None,
    codeset_id: int | None,
    first: bool,
    occurrence_start_date: NormalizedDateRange | None,
    occurrence_end_date: NormalizedDateRange | None,
) -> NormalizedCriterion:
    return NormalizedCriterion(
        raw_criteria=criteria,
        criterion_type=criterion_type,
        domain=domain,
        source_table=source_table,
        event_id_column=event_id_column,
        start_date_column=start_date_column,
        end_date_column=end_date_column,
        concept_column=concept_column,
        source_concept_column=source_concept_column,
        visit_occurrence_column=visit_occurrence_column,
        codeset_id=codeset_id,
        first=first,
        occurrence_start_date=occurrence_start_date,
        occurrence_end_date=occurrence_end_date,
        person_filters=_person_filters_from_criterion(criteria),
    )


def _normalize_condition_occurrence(criteria: ConditionOccurrence) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="ConditionOccurrence",
        domain="condition_occurrence",
        source_table="condition_occurrence",
        event_id_column="condition_occurrence_id",
        start_date_column="condition_start_date",
        end_date_column="condition_end_date",
        concept_column="condition_concept_id",
        source_concept_column="condition_source_concept_id",
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.occurrence_start_date),
        occurrence_end_date=normalize_date_range(criteria.occurrence_end_date),
    )


def _normalize_drug_exposure(criteria: DrugExposure) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="DrugExposure",
        domain="drug_exposure",
        source_table="drug_exposure",
        event_id_column="drug_exposure_id",
        start_date_column="drug_exposure_start_date",
        end_date_column="drug_exposure_end_date",
        concept_column="drug_concept_id",
        source_concept_column="drug_source_concept_id",
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.occurrence_start_date),
        occurrence_end_date=normalize_date_range(criteria.occurrence_end_date),
    )


def _normalize_visit_occurrence(criteria: VisitOccurrence) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="VisitOccurrence",
        domain="visit_occurrence",
        source_table="visit_occurrence",
        event_id_column="visit_occurrence_id",
        start_date_column="visit_start_date",
        end_date_column="visit_end_date",
        concept_column="visit_concept_id",
        source_concept_column="visit_source_concept_id",
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.occurrence_start_date),
        occurrence_end_date=normalize_date_range(criteria.occurrence_end_date),
    )


def _normalize_measurement(criteria: Measurement) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="Measurement",
        domain="measurement",
        source_table="measurement",
        event_id_column="measurement_id",
        start_date_column="measurement_date",
        end_date_column="measurement_date",
        concept_column="measurement_concept_id",
        source_concept_column="measurement_source_concept_id",
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.occurrence_start_date),
        occurrence_end_date=normalize_date_range(criteria.occurrence_end_date),
    )


def _normalize_procedure_occurrence(
    criteria: ProcedureOccurrence,
) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="ProcedureOccurrence",
        domain="procedure_occurrence",
        source_table="procedure_occurrence",
        event_id_column="procedure_occurrence_id",
        start_date_column="procedure_date",
        end_date_column="procedure_date",
        concept_column="procedure_concept_id",
        source_concept_column="procedure_source_concept_id",
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.occurrence_start_date),
        occurrence_end_date=normalize_date_range(criteria.occurrence_end_date),
    )


def _normalize_observation(criteria: Observation) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="Observation",
        domain="observation",
        source_table="observation",
        event_id_column="observation_id",
        start_date_column="observation_date",
        end_date_column="observation_date",
        concept_column="observation_concept_id",
        source_concept_column="observation_source_concept_id",
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.occurrence_start_date),
        occurrence_end_date=normalize_date_range(criteria.occurrence_end_date),
    )


def _normalize_visit_detail(criteria: VisitDetail) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="VisitDetail",
        domain="visit_detail",
        source_table="visit_detail",
        event_id_column="visit_detail_id",
        start_date_column="visit_detail_start_date",
        end_date_column="visit_detail_end_date",
        concept_column="visit_detail_concept_id",
        source_concept_column="visit_detail_source_concept_id",
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.visit_detail_start_date),
        occurrence_end_date=normalize_date_range(criteria.visit_detail_end_date),
    )


def _normalize_device_exposure(criteria: DeviceExposure) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="DeviceExposure",
        domain="device_exposure",
        source_table="device_exposure",
        event_id_column="device_exposure_id",
        start_date_column="device_exposure_start_date",
        end_date_column="device_exposure_end_date",
        concept_column="device_concept_id",
        source_concept_column="device_source_concept_id",
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.occurrence_start_date),
        occurrence_end_date=normalize_date_range(criteria.occurrence_end_date),
    )


def _normalize_specimen(criteria: Specimen) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="Specimen",
        domain="specimen",
        source_table="specimen",
        event_id_column="specimen_id",
        start_date_column="specimen_date",
        end_date_column="specimen_date",
        concept_column="specimen_concept_id",
        source_concept_column="specimen_source_concept_id",
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.occurrence_start_date),
        occurrence_end_date=normalize_date_range(criteria.occurrence_end_date),
    )


def _normalize_death(criteria: Death) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="Death",
        domain="death",
        source_table="death",
        event_id_column="person_id",
        start_date_column="death_date",
        end_date_column="death_date",
        concept_column="cause_concept_id",
        source_concept_column="cause_source_concept_id",
        visit_occurrence_column=None,
        codeset_id=criteria.codeset_id,
        first=False,
        occurrence_start_date=normalize_date_range(criteria.occurrence_start_date),
        occurrence_end_date=None,
    )


def _normalize_observation_period(criteria: ObservationPeriod) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="ObservationPeriod",
        domain="observation_period",
        source_table="observation_period",
        event_id_column="observation_period_id",
        start_date_column="observation_period_start_date",
        end_date_column="observation_period_end_date",
        concept_column="period_type_concept_id",
        source_concept_column=None,
        visit_occurrence_column=None,
        codeset_id=None,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.period_start_date),
        occurrence_end_date=normalize_date_range(criteria.period_end_date),
    )


def _normalize_payer_plan_period(criteria: PayerPlanPeriod) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="PayerPlanPeriod",
        domain="payer_plan_period",
        source_table="payer_plan_period",
        event_id_column="payer_plan_period_id",
        start_date_column="payer_plan_period_start_date",
        end_date_column="payer_plan_period_end_date",
        concept_column="payer_concept_id",
        source_concept_column="payer_source_concept_id",
        visit_occurrence_column=None,
        codeset_id=None,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.period_start_date),
        occurrence_end_date=normalize_date_range(criteria.period_end_date),
    )


def _normalize_condition_era(criteria: ConditionEra) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="ConditionEra",
        domain="condition_era",
        source_table="condition_era",
        event_id_column="condition_era_id",
        start_date_column="condition_era_start_date",
        end_date_column="condition_era_end_date",
        concept_column="condition_concept_id",
        source_concept_column=None,
        visit_occurrence_column=None,
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.era_start_date),
        occurrence_end_date=normalize_date_range(criteria.era_end_date),
    )


def _normalize_drug_era(criteria: DrugEra) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="DrugEra",
        domain="drug_era",
        source_table="drug_era",
        event_id_column="drug_era_id",
        start_date_column="drug_era_start_date",
        end_date_column="drug_era_end_date",
        concept_column="drug_concept_id",
        source_concept_column=None,
        visit_occurrence_column=None,
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.era_start_date),
        occurrence_end_date=normalize_date_range(criteria.era_end_date),
    )


def _normalize_dose_era(criteria: DoseEra) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="DoseEra",
        domain="dose_era",
        source_table="dose_era",
        event_id_column="dose_era_id",
        start_date_column="dose_era_start_date",
        end_date_column="dose_era_end_date",
        concept_column="drug_concept_id",
        source_concept_column=None,
        visit_occurrence_column=None,
        codeset_id=criteria.codeset_id,
        first=bool(criteria.first),
        occurrence_start_date=normalize_date_range(criteria.era_start_date),
        occurrence_end_date=normalize_date_range(criteria.era_end_date),
    )


def _normalize_location_region(criteria: LocationRegion) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="LocationRegion",
        domain="location_region",
        source_table="location_history",
        event_id_column="location_id",
        start_date_column="start_date",
        end_date_column="end_date",
        concept_column="region_concept_id",
        source_concept_column=None,
        visit_occurrence_column=None,
        codeset_id=criteria.codeset_id,
        first=False,
        occurrence_start_date=None,
        occurrence_end_date=None,
    )


def normalize_criterion(criteria: Criteria) -> NormalizedCriterion:
    if isinstance(criteria, ConditionOccurrence):
        normalized = _normalize_condition_occurrence(criteria)
    elif isinstance(criteria, DrugExposure):
        normalized = _normalize_drug_exposure(criteria)
    elif isinstance(criteria, VisitOccurrence):
        normalized = _normalize_visit_occurrence(criteria)
    elif isinstance(criteria, Measurement):
        normalized = _normalize_measurement(criteria)
    elif isinstance(criteria, ProcedureOccurrence):
        normalized = _normalize_procedure_occurrence(criteria)
    elif isinstance(criteria, Observation):
        normalized = _normalize_observation(criteria)
    elif isinstance(criteria, VisitDetail):
        normalized = _normalize_visit_detail(criteria)
    elif isinstance(criteria, DeviceExposure):
        normalized = _normalize_device_exposure(criteria)
    elif isinstance(criteria, Specimen):
        normalized = _normalize_specimen(criteria)
    elif isinstance(criteria, Death):
        normalized = _normalize_death(criteria)
    elif isinstance(criteria, ObservationPeriod):
        normalized = _normalize_observation_period(criteria)
    elif isinstance(criteria, PayerPlanPeriod):
        normalized = _normalize_payer_plan_period(criteria)
    elif isinstance(criteria, ConditionEra):
        normalized = _normalize_condition_era(criteria)
    elif isinstance(criteria, DrugEra):
        normalized = _normalize_drug_era(criteria)
    elif isinstance(criteria, DoseEra):
        normalized = _normalize_dose_era(criteria)
    elif isinstance(criteria, LocationRegion):
        normalized = _normalize_location_region(criteria)
    else:
        raise UnsupportedCriterionError(
            f"Unsupported criterion for Ibis executor: {criteria.__class__.__name__}"
        )

    if (
        criteria.correlated_criteria is not None
        and not criteria.correlated_criteria.is_empty()
    ):
        from .groups import normalize_criteria_group

        normalized_group = normalize_criteria_group(criteria.correlated_criteria)
        normalized = replace(normalized, correlated_criteria=normalized_group)

    return normalized
