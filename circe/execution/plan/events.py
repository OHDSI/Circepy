from __future__ import annotations

from typing import Any, Union

from .._dataclass import frozen_slots_dataclass
from .predicates import DateRangePredicate, NumericRangePredicate
from .schema import PERSON_ID


@frozen_slots_dataclass
class EventSource:
    table_name: str
    domain: str
    event_id_column: str
    start_date_column: str
    end_date_column: str
    person_id_column: str = PERSON_ID
    concept_column: str | None = None
    source_concept_column: str | None = None
    visit_occurrence_column: str | None = None


@frozen_slots_dataclass
class FilterByCodeset:
    column: str
    codeset_id: int
    exclude: bool = False


@frozen_slots_dataclass
class FilterByConceptSet:
    column: str
    concept_ids: tuple[int, ...]
    exclude: bool = False


@frozen_slots_dataclass
class FilterByDateRange:
    column: str
    predicate: DateRangePredicate


@frozen_slots_dataclass
class FilterByNumericRange:
    column: str
    predicate: NumericRangePredicate


@frozen_slots_dataclass
class FilterByText:
    column: str
    op: str | None
    text: str | None


@frozen_slots_dataclass
class JoinLocationRegion:
    location_id_column: str = "location_id"
    region_column: str = "region_concept_id"


@frozen_slots_dataclass
class FilterByVisit:
    visit_occurrence_column: str = "visit_occurrence_id"
    concept_ids: tuple[int, ...] = ()
    codeset_id: int | None = None
    exclude: bool = False


@frozen_slots_dataclass
class FilterByVisitDetail:
    visit_detail_codeset_id: int | None = None


@frozen_slots_dataclass
class FilterByProviderSpecialty:
    provider_id_column: str = "provider_id"
    concept_ids: tuple[int, ...] = ()
    codeset_id: int | None = None
    exclude: bool = False


@frozen_slots_dataclass
class FilterByCareSite:
    care_site_id_column: str = "care_site_id"
    concept_ids: tuple[int, ...] = ()
    codeset_id: int | None = None
    exclude: bool = False


@frozen_slots_dataclass
class FilterByCareSiteLocationRegion:
    care_site_id_column: str = "care_site_id"
    start_date_column: str = "start_date"
    end_date_column: str = "end_date"
    codeset_id: int = 0


@frozen_slots_dataclass
class FilterByPersonAge:
    date_column: str
    predicate: NumericRangePredicate


@frozen_slots_dataclass
class FilterByPersonGender:
    concept_ids: tuple[int, ...] = ()
    codeset_id: int | None = None


@frozen_slots_dataclass
class FilterByPersonRace:
    concept_ids: tuple[int, ...] = ()
    codeset_id: int | None = None


@frozen_slots_dataclass
class FilterByPersonEthnicity:
    concept_ids: tuple[int, ...] = ()
    codeset_id: int | None = None


@frozen_slots_dataclass
class KeepFirstPerPerson:
    order_by: tuple[str, ...]


@frozen_slots_dataclass
class ApplyDateAdjustment:
    start_offset_days: int
    end_offset_days: int
    start_with: str = "start_date"
    end_with: str = "end_date"


@frozen_slots_dataclass
class RestrictToCorrelatedWindow:
    payload: dict[str, Any]


@frozen_slots_dataclass
class StandardizeEventShape:
    criterion_type: str
    criterion_index: int
    start_offset_days: int = 0
    end_offset_days: int = 0
    start_with: str = "start_date"
    end_with: str = "end_date"


PlanStep = Union[
    FilterByCodeset,
    FilterByConceptSet,
    FilterByDateRange,
    FilterByNumericRange,
    FilterByText,
    JoinLocationRegion,
    FilterByVisit,
    FilterByVisitDetail,
    FilterByProviderSpecialty,
    FilterByCareSite,
    FilterByCareSiteLocationRegion,
    FilterByPersonAge,
    FilterByPersonGender,
    FilterByPersonRace,
    FilterByPersonEthnicity,
    KeepFirstPerPerson,
    ApplyDateAdjustment,
    RestrictToCorrelatedWindow,
    StandardizeEventShape,
]


@frozen_slots_dataclass
class EventPlan:
    source: EventSource
    criterion_type: str
    criterion_index: int
    steps: tuple[PlanStep, ...]
