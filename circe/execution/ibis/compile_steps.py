from __future__ import annotations

import ibis

from ..errors import CompilationError, UnsupportedFeatureError
from ..plan.events import (
    ApplyDateAdjustment,
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
    JoinLocationRegion,
    KeepFirstPerPerson,
    RestrictToCorrelatedWindow,
    StandardizeEventShape,
)
from ..plan.predicates import DateRangePredicate, NumericRangePredicate
from ..plan.schema import END_DATE, PERSON_ID, START_DATE
from .context import ExecutionContext
from .person_filters import (
    apply_person_age_filter,
    apply_person_ethnicity_filter,
    apply_person_gender_filter,
    apply_person_race_filter,
)
from .standardize import standardize_event_table


def _apply_numeric_predicate(expr, predicate: NumericRangePredicate):
    op = (predicate.op or "eq").lower()
    value = predicate.value
    extent = predicate.extent

    if value is None:
        return ibis.literal(True)

    if op in {"eq", "="}:
        return expr == value
    if op in {"neq", "!=", "ne"}:
        return expr != value
    if op in {"gt", ">"}:
        return expr > value
    if op in {"gte", ">="}:
        return expr >= value
    if op in {"lt", "<"}:
        return expr < value
    if op in {"lte", "<="}:
        return expr <= value
    if op in {"bt", "between"}:
        if extent is None:
            raise CompilationError(
                "Ibis executor compilation error: numeric range 'between' requires an extent value."
            )
        lower = min(value, extent)
        upper = max(value, extent)
        return (expr >= lower) & (expr <= upper)

    raise CompilationError(f"Ibis executor compilation error: unsupported numeric range op {predicate.op!r}.")


def _apply_date_predicate(expr, predicate: DateRangePredicate):
    op = (predicate.op or "eq").lower()
    value = predicate.value
    extent = predicate.extent

    if value is None:
        return ibis.literal(True)

    value_expr = ibis.literal(value).cast("date")

    if op in {"eq", "="}:
        return expr.cast("date") == value_expr
    if op in {"neq", "!=", "ne"}:
        return expr.cast("date") != value_expr
    if op in {"gt", ">"}:
        return expr.cast("date") > value_expr
    if op in {"gte", ">="}:
        return expr.cast("date") >= value_expr
    if op in {"lt", "<"}:
        return expr.cast("date") < value_expr
    if op in {"lte", "<="}:
        return expr.cast("date") <= value_expr
    if op in {"bt", "between"}:
        if extent is None:
            raise CompilationError(
                "Ibis executor compilation error: date range 'between' requires an extent value."
            )
        extent_expr = ibis.literal(extent).cast("date")
        lower = ibis.least(value_expr, extent_expr)
        upper = ibis.greatest(value_expr, extent_expr)
        return (expr.cast("date") >= lower) & (expr.cast("date") <= upper)

    raise CompilationError(f"Ibis executor compilation error: unsupported date range op {predicate.op!r}.")


def _select_original_columns(table, joined):
    return joined.select(*[joined[c] for c in table.columns])


def _filter_by_concept_table(table, concept_table, *, column, exclude=False):
    """Semi-join (include) or anti-join (exclude) *table* against *concept_table*."""
    if not exclude:
        joined = table.join(concept_table, table[column] == concept_table.concept_id)
        return _select_original_columns(table, joined)
    else:
        marked = concept_table.mutate(_cm=ibis.literal(1, type="int64"))
        joined = table.join(marked, table[column] == marked.concept_id, how="left")
        filtered = joined.filter(joined._cm.isnull())
        return _select_original_columns(table, filtered)


def _filter_visit_concepts(table, ctx: ExecutionContext, *, step: FilterByVisit):
    visit = ctx.table("visit_occurrence")
    visit_lookup = visit.select(
        visit.visit_occurrence_id.name("_visit_occurrence_id"),
        visit.person_id.name("_visit_person_id"),
        visit.visit_concept_id.name("_visit_concept_id"),
    )
    joined = table.join(
        visit_lookup,
        predicates=[
            table[step.visit_occurrence_column] == visit_lookup._visit_occurrence_id,
            table[PERSON_ID] == visit_lookup._visit_person_id,
        ],
    )

    if step.codeset_id is not None:
        concept_table = ctx.concept_set_table(step.codeset_id)
        joined = joined.join(concept_table, joined._visit_concept_id == concept_table.concept_id)
    elif step.concept_ids:
        concept_table = ibis.memtable(
            {"concept_id": list(step.concept_ids)}, schema={"concept_id": "int64"}
        )
        joined = joined.join(concept_table, joined._visit_concept_id == concept_table.concept_id)
    # If neither codeset_id nor concept_ids, no filtering needed

    if step.exclude:
        marked = concept_table.mutate(_cm=ibis.literal(1, type="int64"))
        joined = joined.join(marked, joined._visit_concept_id == marked.concept_id, how="left")
        joined = joined.filter(joined._cm.isnull())
        return _select_original_columns(table, joined)

    return _select_original_columns(table, joined)


def _filter_provider_specialty(
    table,
    ctx: ExecutionContext,
    *,
    step: FilterByProviderSpecialty,
):
    provider = ctx.table("provider")
    provider_lookup = provider.select(
        provider.provider_id.name("_provider_id"),
        provider.specialty_concept_id.name("_specialty_concept_id"),
    )
    joined = table.join(
        provider_lookup,
        predicates=[table[step.provider_id_column] == provider_lookup._provider_id],
    )

    if step.codeset_id is not None:
        concept_table = ctx.concept_set_table(step.codeset_id)
        joined = joined.join(concept_table, joined._specialty_concept_id == concept_table.concept_id)
    elif step.concept_ids:
        concept_table = ibis.memtable(
            {"concept_id": list(step.concept_ids)}, schema={"concept_id": "int64"}
        )
        joined = joined.join(concept_table, joined._specialty_concept_id == concept_table.concept_id)

    if step.exclude:
        marked = concept_table.mutate(_cm=ibis.literal(1, type="int64"))
        joined = joined.join(marked, joined._specialty_concept_id == marked.concept_id, how="left")
        joined = joined.filter(joined._cm.isnull())
        return _select_original_columns(table, joined)

    return _select_original_columns(table, joined)


def _filter_care_site(table, ctx: ExecutionContext, *, step: FilterByCareSite):
    care_site = ctx.table("care_site")
    care_site_lookup = care_site.select(
        care_site.care_site_id.name("_care_site_id"),
        care_site.place_of_service_concept_id.name("_place_of_service_concept_id"),
    )
    joined = table.join(
        care_site_lookup,
        predicates=[table[step.care_site_id_column] == care_site_lookup._care_site_id],
    )

    if step.codeset_id is not None:
        concept_table = ctx.concept_set_table(step.codeset_id)
        joined = joined.join(concept_table, joined._place_of_service_concept_id == concept_table.concept_id)
    elif step.concept_ids:
        concept_table = ibis.memtable(
            {"concept_id": list(step.concept_ids)}, schema={"concept_id": "int64"}
        )
        joined = joined.join(concept_table, joined._place_of_service_concept_id == concept_table.concept_id)

    if step.exclude:
        marked = concept_table.mutate(_cm=ibis.literal(1, type="int64"))
        joined = joined.join(marked, joined._place_of_service_concept_id == marked.concept_id, how="left")
        joined = joined.filter(joined._cm.isnull())
        return _select_original_columns(table, joined)

    return _select_original_columns(table, joined)


def _filter_care_site_location_region(
    table,
    ctx: ExecutionContext,
    *,
    step: FilterByCareSiteLocationRegion,
):
    concept_table = ctx.concept_set_table(step.codeset_id)

    location_history = ctx.table("location_history")
    history_lookup = location_history.select(
        location_history.entity_id.name("_care_site_id"),
        location_history.location_id.name("_history_location_id"),
        location_history.domain_id.name("_history_domain_id"),
        location_history.start_date.name("_history_start_date"),
        location_history.end_date.name("_history_end_date"),
    )
    joined_history = table.join(
        history_lookup,
        predicates=[table[step.care_site_id_column] == history_lookup._care_site_id],
    )
    history_end = ibis.coalesce(
        joined_history._history_end_date.cast("date"),
        ibis.literal("2099-12-31").cast("date"),
    )
    joined_history = joined_history.filter(
        (joined_history._history_domain_id == "CARE_SITE")
        & (
            joined_history[step.start_date_column].cast("date")
            >= joined_history._history_start_date.cast("date")
        )
        & (joined_history[step.end_date_column].cast("date") <= history_end)
    )

    location = ctx.table("location")
    location_lookup = location.select(
        location.location_id.name("_location_id"),
        location.region_concept_id.name("_region_concept_id"),
    )
    joined = joined_history.join(
        location_lookup,
        predicates=[joined_history._history_location_id == location_lookup._location_id],
    )

    joined = joined.join(concept_table, joined._region_concept_id == concept_table.concept_id)
    return _select_original_columns(table, joined)


def apply_step(step, *, table, source, ctx: ExecutionContext):
    if isinstance(step, JoinLocationRegion):
        location = ctx.table("location").select(
            "location_id",
            step.region_column,
        )
        joined = table.join(
            location,
            predicates=[table[step.location_id_column] == location.location_id],
        )
        return joined.select(
            *[joined[c] for c in table.columns],
            location[step.region_column].name(step.region_column),
        )

    if isinstance(step, FilterByCodeset):
        concept_table = ctx.concept_set_table(step.codeset_id)
        return _filter_by_concept_table(
            table, concept_table, column=step.column, exclude=step.exclude
        )

    if isinstance(step, FilterByConceptSet):
        if not step.concept_ids:
            return table if step.exclude else table.limit(0)
        concept_table = ibis.memtable(
            {"concept_id": list(step.concept_ids)}, schema={"concept_id": "int64"}
        )
        return _filter_by_concept_table(
            table, concept_table, column=step.column, exclude=step.exclude
        )

    if isinstance(step, FilterByVisit):
        return _filter_visit_concepts(table, ctx, step=step)

    if isinstance(step, FilterByProviderSpecialty):
        return _filter_provider_specialty(table, ctx, step=step)

    if isinstance(step, FilterByCareSite):
        return _filter_care_site(table, ctx, step=step)

    if isinstance(step, FilterByCareSiteLocationRegion):
        return _filter_care_site_location_region(table, ctx, step=step)

    if isinstance(step, FilterByDateRange):
        return table.filter(_apply_date_predicate(table[step.column], step.predicate))

    if isinstance(step, FilterByNumericRange):
        return table.filter(_apply_numeric_predicate(table[step.column], step.predicate))

    if isinstance(step, FilterByText):
        op = (step.op or "eq").lower()
        if step.text is None:
            return table
        if op in {"eq", "="}:
            return table.filter(table[step.column] == step.text)
        if op in {"neq", "!=", "ne"}:
            return table.filter(table[step.column] != step.text)
        if op in {"contains", "like"}:
            return table.filter(table[step.column].contains(step.text))
        raise CompilationError(f"Ibis executor compilation error: unsupported text filter op {step.op!r}.")

    if isinstance(step, FilterByPersonAge):
        return apply_person_age_filter(
            table,
            ctx,
            date_column=step.date_column,
            predicate=step.predicate,
        )

    if isinstance(step, FilterByPersonGender):
        return apply_person_gender_filter(
            table,
            ctx,
            concept_ids=step.concept_ids,
            codeset_id=step.codeset_id,
        )

    if isinstance(step, FilterByPersonRace):
        return apply_person_race_filter(
            table,
            ctx,
            concept_ids=step.concept_ids,
            codeset_id=step.codeset_id,
        )

    if isinstance(step, FilterByPersonEthnicity):
        return apply_person_ethnicity_filter(
            table,
            ctx,
            concept_ids=step.concept_ids,
            codeset_id=step.codeset_id,
        )

    if isinstance(step, KeepFirstPerPerson):
        order_by = [table[c] for c in step.order_by if c in table.columns]
        window = ibis.window(group_by=table[PERSON_ID], order_by=order_by)
        ranked = table.mutate(_exec_rn=ibis.row_number().over(window))
        return ranked.filter(ranked._exec_rn == 0).drop("_exec_rn")

    if isinstance(step, ApplyDateAdjustment):
        start_anchor = table[START_DATE] if step.start_with == START_DATE else table[END_DATE]
        end_anchor = table[START_DATE] if step.end_with == START_DATE else table[END_DATE]
        return table.mutate(
            **{
                START_DATE: start_anchor + ibis.interval(days=step.start_offset_days),
                END_DATE: end_anchor + ibis.interval(days=step.end_offset_days),
            }
        )

    if isinstance(step, RestrictToCorrelatedWindow):
        raise UnsupportedFeatureError(
            "Ibis executor compilation error: RestrictToCorrelatedWindow step is not implemented."
        )

    if isinstance(step, StandardizeEventShape):
        return standardize_event_table(
            table,
            source=source,
            criterion_type=step.criterion_type,
            criterion_index=step.criterion_index,
            start_offset_days=step.start_offset_days,
            end_offset_days=step.end_offset_days,
            start_with=step.start_with,
            end_with=step.end_with,
        )

    raise CompilationError(
        f"Ibis executor compilation error: unsupported plan step {step.__class__.__name__}."
    )
