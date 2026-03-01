from __future__ import annotations

from typing import List

from ...cohortdefinition.core import ConceptSetSelection, NumericRange, TextFilter
from ...vocabulary.concept import Concept
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import (
    EventPlan,
    EventSource,
    FilterByCodeset,
    FilterByConceptSet,
    FilterByDateRange,
    FilterByNumericRange,
    FilterByPersonAge,
    FilterByPersonEthnicity,
    FilterByPersonGender,
    FilterByPersonRace,
    FilterByText,
    KeepFirstPerPerson,
    PlanStep,
    StandardizeEventShape,
)
from ..plan.predicates import DateRangePredicate, NumericRangePredicate


def lower_common_steps(criterion: NormalizedCriterion) -> List[PlanStep]:
    steps: List[PlanStep] = []

    if criterion.codeset_id is not None and criterion.concept_column is not None:
        steps.append(
            FilterByCodeset(
                column=criterion.concept_column,
                codeset_id=int(criterion.codeset_id),
            )
        )

    if criterion.occurrence_start_date is not None:
        steps.append(
            FilterByDateRange(
                column=criterion.start_date_column,
                predicate=DateRangePredicate(
                    op=criterion.occurrence_start_date.op,
                    value=criterion.occurrence_start_date.value,
                    extent=criterion.occurrence_start_date.extent,
                ),
            )
        )

    if criterion.occurrence_end_date is not None:
        steps.append(
            FilterByDateRange(
                column=criterion.end_date_column,
                predicate=DateRangePredicate(
                    op=criterion.occurrence_end_date.op,
                    value=criterion.occurrence_end_date.value,
                    extent=criterion.occurrence_end_date.extent,
                ),
            )
        )

    if criterion.person_filters.age is not None:
        steps.append(
            FilterByPersonAge(
                date_column=criterion.start_date_column,
                predicate=NumericRangePredicate(
                    op=criterion.person_filters.age.op,
                    value=criterion.person_filters.age.value,
                    extent=criterion.person_filters.age.extent,
                ),
            )
        )

    if (
        criterion.person_filters.gender_concept_ids
        or criterion.person_filters.gender_codeset_id is not None
    ):
        steps.append(
            FilterByPersonGender(
                concept_ids=criterion.person_filters.gender_concept_ids,
                codeset_id=criterion.person_filters.gender_codeset_id,
            )
        )

    if (
        criterion.person_filters.race_concept_ids
        or criterion.person_filters.race_codeset_id is not None
    ):
        steps.append(
            FilterByPersonRace(
                concept_ids=criterion.person_filters.race_concept_ids,
                codeset_id=criterion.person_filters.race_codeset_id,
            )
        )

    if (
        criterion.person_filters.ethnicity_concept_ids
        or criterion.person_filters.ethnicity_codeset_id is not None
    ):
        steps.append(
            FilterByPersonEthnicity(
                concept_ids=criterion.person_filters.ethnicity_concept_ids,
                codeset_id=criterion.person_filters.ethnicity_codeset_id,
            )
        )

    if criterion.first:
        steps.append(
            KeepFirstPerPerson(
                order_by=(criterion.start_date_column, criterion.event_id_column),
            )
        )

    return steps


def concept_ids(values: list[Concept] | None) -> tuple[int, ...]:
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


def append_numeric_filter(
    steps: list[PlanStep],
    *,
    column: str,
    value: NumericRange | None,
) -> None:
    if value is None:
        return
    steps.append(
        FilterByNumericRange(
            column=column,
            predicate=NumericRangePredicate(
                op=value.op,
                value=value.value,
                extent=value.extent,
            ),
        )
    )


def append_text_filter(
    steps: list[PlanStep],
    *,
    column: str,
    value: TextFilter | None,
) -> None:
    if value is None:
        return
    steps.append(
        FilterByText(
            column=column,
            op=value.op,
            text=value.text,
        )
    )


def append_concept_filters(
    steps: list[PlanStep],
    *,
    column: str,
    concepts: list[Concept] | None = None,
    codeset_selection: ConceptSetSelection | None = None,
    exclude: bool = False,
) -> None:
    ids = concept_ids(concepts)
    if ids:
        steps.append(
            FilterByConceptSet(
                column=column,
                concept_ids=ids,
                exclude=bool(exclude),
            )
        )

    if codeset_selection and codeset_selection.codeset_id is not None:
        steps.append(
            FilterByCodeset(
                column=column,
                codeset_id=int(codeset_selection.codeset_id),
                exclude=bool(codeset_selection.is_exclusion) or bool(exclude),
            )
        )


def build_standard_domain_plan(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
    steps: list[PlanStep],
) -> EventPlan:
    steps.append(
        StandardizeEventShape(
            criterion_type=criterion.criterion_type,
            criterion_index=criterion_index,
        )
    )
    return EventPlan(
        source=EventSource(
            table_name=criterion.source_table,
            domain=criterion.domain,
            event_id_column=criterion.event_id_column,
            start_date_column=criterion.start_date_column,
            end_date_column=criterion.end_date_column,
            concept_column=criterion.concept_column,
            source_concept_column=criterion.source_concept_column,
            visit_occurrence_column=criterion.visit_occurrence_column,
        ),
        criterion_type=criterion.criterion_type,
        criterion_index=criterion_index,
        steps=tuple(steps),
    )


def lower_standard_domain_plan(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    steps = lower_common_steps(criterion)
    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
    )
