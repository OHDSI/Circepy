from __future__ import annotations

from ...cohortdefinition.criteria import (
    CorelatedCriteria,
    CriteriaGroup,
    DemographicCriteria,
    InclusionRule,
    Occurrence,
)
from ...vocabulary.concept import Concept
from .._dataclass import frozen_slots_dataclass
from .criteria import NormalizedCriterion, normalize_criterion
from .windows import (
    NormalizedDateRange,
    NormalizedNumericRange,
    NormalizedWindow,
    normalize_date_range,
    normalize_numeric_range,
    normalize_window,
)


@frozen_slots_dataclass
class NormalizedDemographicCriteria:
    age: NormalizedNumericRange | None = None
    gender_codeset_id: int | None = None
    gender_concept_ids: tuple[int, ...] = ()
    race_codeset_id: int | None = None
    race_concept_ids: tuple[int, ...] = ()
    ethnicity_codeset_id: int | None = None
    ethnicity_concept_ids: tuple[int, ...] = ()
    occurrence_start_date: NormalizedDateRange | None = None
    occurrence_end_date: NormalizedDateRange | None = None


@frozen_slots_dataclass
class NormalizedCorrelatedCriteria:
    criterion: NormalizedCriterion
    occurrence_type: int
    occurrence_count: int
    occurrence_is_distinct: bool
    occurrence_count_column: str | None
    start_window: NormalizedWindow | None
    end_window: NormalizedWindow | None
    restrict_visit: bool
    ignore_observation_period: bool


@frozen_slots_dataclass
class NormalizedCriteriaGroup:
    mode: str
    count: int | None = None
    criteria: tuple[NormalizedCorrelatedCriteria, ...] = ()
    groups: tuple[NormalizedCriteriaGroup, ...] = ()
    demographics: tuple[NormalizedDemographicCriteria, ...] = ()

    def is_empty(self) -> bool:
        return not self.criteria and not self.groups and not self.demographics


@frozen_slots_dataclass
class NormalizedInclusionRule:
    name: str | None
    description: str | None
    expression: NormalizedCriteriaGroup | None


def _concept_ids(values: list[Concept] | None) -> tuple[int, ...]:
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


def _normalize_demographic(
    demographic: DemographicCriteria,
) -> NormalizedDemographicCriteria:
    return NormalizedDemographicCriteria(
        age=normalize_numeric_range(demographic.age),
        gender_codeset_id=(
            int(demographic.gender_cs.codeset_id)
            if demographic.gender_cs and demographic.gender_cs.codeset_id is not None
            else None
        ),
        gender_concept_ids=_concept_ids(demographic.gender),
        race_codeset_id=(
            int(demographic.race_cs.codeset_id)
            if demographic.race_cs and demographic.race_cs.codeset_id is not None
            else None
        ),
        race_concept_ids=_concept_ids(demographic.race),
        ethnicity_codeset_id=(
            int(demographic.ethnicity_cs.codeset_id)
            if demographic.ethnicity_cs and demographic.ethnicity_cs.codeset_id is not None
            else None
        ),
        ethnicity_concept_ids=_concept_ids(demographic.ethnicity),
        occurrence_start_date=normalize_date_range(demographic.occurrence_start_date),
        occurrence_end_date=normalize_date_range(demographic.occurrence_end_date),
    )


def _normalize_correlated_criteria(
    correlated: CorelatedCriteria,
) -> NormalizedCorrelatedCriteria:
    occurrence = correlated.occurrence or Occurrence(
        type=Occurrence._AT_LEAST,
        count=1,
        is_distinct=False,
    )

    count_column = None
    if occurrence.count_column is not None:
        count_column = occurrence.count_column.value

    return NormalizedCorrelatedCriteria(
        criterion=normalize_criterion(correlated.criteria),
        occurrence_type=int(occurrence.type),
        occurrence_count=int(occurrence.count),
        occurrence_is_distinct=bool(occurrence.is_distinct),
        occurrence_count_column=count_column,
        start_window=normalize_window(correlated.start_window),
        end_window=normalize_window(correlated.end_window),
        restrict_visit=bool(correlated.restrict_visit),
        ignore_observation_period=bool(correlated.ignore_observation_period),
    )


def normalize_criteria_group(
    group: CriteriaGroup | None,
) -> NormalizedCriteriaGroup | None:
    if group is None:
        return None

    normalized_children: list[NormalizedCriteriaGroup] = []
    for child in group.groups or []:
        normalized_child = normalize_criteria_group(child)
        if normalized_child is not None:
            normalized_children.append(normalized_child)

    return NormalizedCriteriaGroup(
        mode=((group.type or "ALL").upper()),
        count=(int(group.count) if group.count is not None else None),
        criteria=tuple(
            _normalize_correlated_criteria(correlated) for correlated in (group.criteria_list or [])
        ),
        groups=tuple(normalized_children),
        demographics=tuple(
            _normalize_demographic(demographic) for demographic in (group.demographic_criteria_list or [])
        ),
    )


def normalize_inclusion_rule(rule: InclusionRule) -> NormalizedInclusionRule:
    return NormalizedInclusionRule(
        name=rule.name,
        description=rule.description,
        expression=normalize_criteria_group(rule.expression),
    )
