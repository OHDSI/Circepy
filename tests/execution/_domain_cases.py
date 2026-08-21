from __future__ import annotations

from collections.abc import Callable

from circe.cohortdefinition import (
    ConditionEra,
    ConditionOccurrence,
    Death,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
    LocationRegion,
    Measurement,
    Observation,
    ObservationPeriod,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
    VisitOccurrence,
)

CriteriaFactory = Callable[[], object]


def domain_criteria_cases() -> list[tuple[str, CriteriaFactory, int | None]]:
    """Domain criteria factories + default concept id used for codeset filters."""
    return [
        ("condition_occurrence", lambda: ConditionOccurrence(codeset_id=1), 111),
        ("drug_exposure", lambda: DrugExposure(codeset_id=1), 222),
        ("visit_occurrence", lambda: VisitOccurrence(codeset_id=1), 333),
        ("measurement", lambda: Measurement(codeset_id=1), 444),
        ("procedure_occurrence", lambda: ProcedureOccurrence(codeset_id=1), 555),
        ("observation", lambda: Observation(codeset_id=1), 666),
        ("visit_detail", lambda: VisitDetail(codeset_id=1), 777),
        ("device_exposure", lambda: DeviceExposure(codeset_id=1), 888),
        ("specimen", lambda: Specimen(codeset_id=1), 999),
        ("death", lambda: Death(codeset_id=1), 1001),
        ("observation_period", lambda: ObservationPeriod(), None),
        ("payer_plan_period", lambda: PayerPlanPeriod(), None),
        ("condition_era", lambda: ConditionEra(codeset_id=1), 1201),
        ("drug_era", lambda: DrugEra(codeset_id=1), 1301),
        ("dose_era", lambda: DoseEra(codeset_id=1), 1401),
        ("location_history", lambda: LocationRegion(codeset_id=1), 15151),
    ]
