from __future__ import annotations

import ibis

from ..errors import CompilationError
from ..plan.events import (
    CollapseCustomEra,
    EventPlan,
    FilterByDateRange,
    FilterByNumericRange,
    FilterByPersonAge,
    FilterByPersonGender,
    KeepFirstPerPerson,
)
from ..plan.predicates import DateRangePredicate, NumericRangePredicate
from ..plan.schema import (
    CONCEPT_ID,
    CRITERION_INDEX,
    CRITERION_TYPE,
    DAYS_SUPPLY,
    DOMAIN,
    DURATION,
    END_DATE,
    EVENT_ID,
    GAP_DAYS,
    OCCURRENCE_COUNT,
    PERSON_ID,
    QUANTITY,
    RANGE_HIGH,
    RANGE_LOW,
    REFILLS,
    SOURCE_CONCEPT_ID,
    SOURCE_TABLE,
    START_DATE,
    UNIT_CONCEPT_ID,
    VALUE_AS_NUMBER,
    VISIT_DETAIL_ID,
    VISIT_OCCURRENCE_ID,
)
from ..typing import Table
from .compile_steps import apply_step
from .context import ExecutionContext


def _compile_custom_era(plan: EventPlan, ctx: ExecutionContext) -> Table:
    from ..engine.custom_era import _compute_eras
    from ..lower.criteria import lower_criterion
    from ..normalize.criteria import normalize_criterion

    step = plan.steps[0]
    assert isinstance(step, CollapseCustomEra)

    if not step.criteria:
        raise CompilationError(
            "Ibis executor compilation error: CustomEra.CriteriaList can not be null or empty."
        )

    nested_tables: list[Table] = []
    for index, raw in enumerate(step.criteria):
        normalized = normalize_criterion(raw)
        nested_plan = lower_criterion(normalized, criterion_index=index)
        nested_table = compile_event_plan(nested_plan, ctx)
        nested_tables.append(
            nested_table.select(
                nested_table[PERSON_ID].name(PERSON_ID),
                nested_table[START_DATE].name(START_DATE),
                nested_table[END_DATE].name(END_DATE),
            )
        )

    exposures = nested_tables[0]
    for nested_table in nested_tables[1:]:
        exposures = exposures.union(nested_table, distinct=False)

    exposures = exposures.mutate(_exposure_end=exposures[END_DATE])

    eras = _compute_eras(exposures, gap_days=step.gap_days, offset=0)

    standardized = eras.mutate(
        _event_id=ibis.row_number().over(
            ibis.window(order_by=[eras[PERSON_ID], eras.era_start_date, eras.era_end_date])
        )
    )
    table = standardized.select(
        standardized[PERSON_ID].cast("int64").name(PERSON_ID),
        standardized._event_id.cast("int64").name(EVENT_ID),
        standardized.era_start_date.cast("date").name(START_DATE),
        standardized.era_end_date.cast("date").name(END_DATE),
        ibis.literal("custom_era").name(DOMAIN),
        ibis.null().cast("int64").name(CONCEPT_ID),
        ibis.null().cast("int64").name(SOURCE_CONCEPT_ID),
        ibis.null().cast("int64").name(VISIT_OCCURRENCE_ID),
        ibis.null().cast("int64").name(VISIT_DETAIL_ID),
        ibis.null().cast("float64").name(QUANTITY),
        ibis.null().cast("float64").name(DAYS_SUPPLY),
        ibis.null().cast("float64").name(REFILLS),
        ibis.null().cast("float64").name(RANGE_LOW),
        ibis.null().cast("float64").name(RANGE_HIGH),
        ibis.null().cast("float64").name(VALUE_AS_NUMBER),
        ibis.null().cast("int64").name(UNIT_CONCEPT_ID),
        ibis.null().cast("int64").name(OCCURRENCE_COUNT),
        ibis.null().cast("int64").name(GAP_DAYS),
        standardized.era_end_date.delta(standardized.era_start_date, unit="day").cast("int64").name(DURATION),
        ibis.literal(int(plan.criterion_index), type="int64").name(CRITERION_INDEX),
        ibis.literal(plan.criterion_type).name(CRITERION_TYPE),
        ibis.literal("custom_era").name(SOURCE_TABLE),
    )

    criterion = step.criterion

    if criterion.person_filters.gender_concept_ids or criterion.person_filters.gender_codeset_id is not None:
        table = apply_step(
            FilterByPersonGender(
                concept_ids=criterion.person_filters.gender_concept_ids,
                codeset_id=criterion.person_filters.gender_codeset_id,
            ),
            table=table,
            source=plan.source,
            ctx=ctx,
        )

    if criterion.person_filters.age is not None:
        age = criterion.person_filters.age
        table = apply_step(
            FilterByPersonAge(
                date_column=START_DATE,
                predicate=NumericRangePredicate(op=age.op, value=age.value, extent=age.extent),
            ),
            table=table,
            source=plan.source,
            ctx=ctx,
        )

    if criterion.occurrence_start_date is not None:
        rng = criterion.occurrence_start_date
        table = apply_step(
            FilterByDateRange(
                column=START_DATE,
                predicate=DateRangePredicate(op=rng.op, value=rng.value, extent=rng.extent),
            ),
            table=table,
            source=plan.source,
            ctx=ctx,
        )

    if criterion.occurrence_end_date is not None:
        rng = criterion.occurrence_end_date
        table = apply_step(
            FilterByDateRange(
                column=END_DATE,
                predicate=DateRangePredicate(op=rng.op, value=rng.value, extent=rng.extent),
            ),
            table=table,
            source=plan.source,
            ctx=ctx,
        )

    duration = getattr(criterion.raw_criteria, "duration", None)
    if duration is not None and duration.op is not None:
        table = apply_step(
            FilterByNumericRange(
                column=DURATION,
                predicate=NumericRangePredicate(op=duration.op, value=duration.value, extent=duration.extent),
            ),
            table=table,
            source=plan.source,
            ctx=ctx,
        )

    if criterion.first:
        table = apply_step(
            KeepFirstPerPerson(order_by=(START_DATE, EVENT_ID)),
            table=table,
            source=plan.source,
            ctx=ctx,
        )

    return table


def compile_event_plan(plan: EventPlan, ctx: ExecutionContext) -> Table:
    if plan.source.table_name == "custom_era":
        return _compile_custom_era(plan, ctx)

    table = ctx.table(plan.source.table_name)
    for step in plan.steps:
        table = apply_step(step, table=table, source=plan.source, ctx=ctx)
    return table
