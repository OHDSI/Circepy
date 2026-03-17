from __future__ import annotations

from ...cohortdefinition.core import ConceptSetSelection, NumericRange, TextFilter
from ...vocabulary.concept import Concept
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import (
    EventPlan,
    EventSource,
    FilterByCareSite,
    FilterByCareSiteLocationRegion,
    FilterByCodeset,
    FilterByConceptSet,
    FilterByDateRange,
    FilterByNumericRange,
    FilterByPersonAge,
    FilterByPersonEthnicity,
    FilterByPersonGender,
    FilterByPersonRace,
    FilterByProviderSpecialty,
    FilterByText,
    FilterByVisit,
    KeepFirstPerPerson,
    PlanStep,
    StandardizeEventShape,
)
from ..plan.predicates import DateRangePredicate, NumericRangePredicate
from ..plan.schema import DURATION, END_DATE, START_DATE


def lower_common_steps(criterion: NormalizedCriterion) -> list[PlanStep]:
    steps: list[PlanStep] = []

    if criterion.codeset_id is not None and criterion.concept_column is not None:
        steps.append(
            FilterByCodeset(
                column=criterion.concept_column,
                codeset_id=int(criterion.codeset_id),
            )
        )

    if criterion.person_filters.gender_concept_ids or criterion.person_filters.gender_codeset_id is not None:
        steps.append(
            FilterByPersonGender(
                concept_ids=criterion.person_filters.gender_concept_ids,
                codeset_id=criterion.person_filters.gender_codeset_id,
            )
        )

    if criterion.person_filters.race_concept_ids or criterion.person_filters.race_codeset_id is not None:
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


def append_visit_filters(
    steps: list[PlanStep],
    *,
    visit_occurrence_column: str,
    concepts: list[Concept] | None = None,
    codeset_selection: ConceptSetSelection | None = None,
    exclude: bool = False,
) -> None:
    ids = concept_ids(concepts)
    if ids:
        steps.append(
            FilterByVisit(
                visit_occurrence_column=visit_occurrence_column,
                concept_ids=ids,
                exclude=bool(exclude),
            )
        )

    if codeset_selection and codeset_selection.codeset_id is not None:
        steps.append(
            FilterByVisit(
                visit_occurrence_column=visit_occurrence_column,
                codeset_id=int(codeset_selection.codeset_id),
                exclude=bool(codeset_selection.is_exclusion),
            )
        )


def append_provider_specialty_filters(
    steps: list[PlanStep],
    *,
    provider_id_column: str = "provider_id",
    concepts: list[Concept] | None = None,
    codeset_selection: ConceptSetSelection | None = None,
) -> None:
    ids = concept_ids(concepts)
    if ids:
        steps.append(
            FilterByProviderSpecialty(
                provider_id_column=provider_id_column,
                concept_ids=ids,
            )
        )

    if codeset_selection and codeset_selection.codeset_id is not None:
        steps.append(
            FilterByProviderSpecialty(
                provider_id_column=provider_id_column,
                codeset_id=int(codeset_selection.codeset_id),
                exclude=bool(codeset_selection.is_exclusion),
            )
        )


def append_care_site_filters(
    steps: list[PlanStep],
    *,
    care_site_id_column: str = "care_site_id",
    concepts: list[Concept] | None = None,
    codeset_selection: ConceptSetSelection | None = None,
) -> None:
    ids = concept_ids(concepts)
    if ids:
        steps.append(
            FilterByCareSite(
                care_site_id_column=care_site_id_column,
                concept_ids=ids,
            )
        )

    if codeset_selection and codeset_selection.codeset_id is not None:
        steps.append(
            FilterByCareSite(
                care_site_id_column=care_site_id_column,
                codeset_id=int(codeset_selection.codeset_id),
                exclude=bool(codeset_selection.is_exclusion),
            )
        )


def append_care_site_location_region_filter(
    steps: list[PlanStep],
    *,
    care_site_id_column: str = "care_site_id",
    start_date_column: str,
    end_date_column: str,
    codeset_id: int | None,
) -> None:
    if codeset_id is None:
        return
    steps.append(
        FilterByCareSiteLocationRegion(
            care_site_id_column=care_site_id_column,
            start_date_column=start_date_column,
            end_date_column=end_date_column,
            codeset_id=int(codeset_id),
        )
    )


def append_post_standardization_common_steps(
    criterion: NormalizedCriterion,
    *,
    steps: list[PlanStep],
) -> None:
    if criterion.person_filters.age is not None:
        steps.append(
            FilterByPersonAge(
                date_column=START_DATE,
                predicate=NumericRangePredicate(
                    op=criterion.person_filters.age.op,
                    value=criterion.person_filters.age.value,
                    extent=criterion.person_filters.age.extent,
                ),
            )
        )

    if criterion.occurrence_start_date is not None:
        steps.append(
            FilterByDateRange(
                column=START_DATE,
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
                column=END_DATE,
                predicate=DateRangePredicate(
                    op=criterion.occurrence_end_date.op,
                    value=criterion.occurrence_end_date.value,
                    extent=criterion.occurrence_end_date.extent,
                ),
            )
        )


def append_duration_filter(
    steps: list[PlanStep],
    *,
    value: NumericRange | None,
) -> None:
    append_numeric_filter(steps, column=DURATION, value=value)


def build_standard_domain_plan(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
    steps: list[PlanStep],
    post_standardize_steps: list[PlanStep] | None = None,
) -> EventPlan:
    plan_steps = list(steps)
    date_adjustment = getattr(criterion.raw_criteria, "date_adjustment", None)
    start_with = START_DATE
    end_with = END_DATE
    start_offset_days = 0
    end_offset_days = 0
    if date_adjustment is not None:
        start_with = (
            date_adjustment.start_with.value
            if getattr(date_adjustment, "start_with", None) is not None
            else START_DATE
        )
        end_with = (
            date_adjustment.end_with.value
            if getattr(date_adjustment, "end_with", None) is not None
            else END_DATE
        )
        start_offset_days = int(date_adjustment.start_offset)
        end_offset_days = int(date_adjustment.end_offset)

    plan_steps.append(
        StandardizeEventShape(
            criterion_type=criterion.criterion_type,
            criterion_index=criterion_index,
            start_offset_days=start_offset_days,
            end_offset_days=end_offset_days,
            start_with=start_with,
            end_with=end_with,
        )
    )

    standard_post_steps = list(post_standardize_steps or [])
    append_post_standardization_common_steps(criterion, steps=standard_post_steps)
    plan_steps.extend(standard_post_steps)

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
        steps=tuple(plan_steps),
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
