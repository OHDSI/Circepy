from __future__ import annotations

from typing import Any, Callable, Optional, Sequence, cast

import ibis
import ibis.expr.types as ir
from ibis.expr.api import row_number

from ...cohortdefinition.core import (
    CollapseSettings,
    CollapseType,
    ConceptSetSelection,
    CustomEraStrategy,
    DateOffsetStrategy,
    DateRange,
    EndStrategy,
    NumericRange,
    TextFilter,
)
from ...vocabulary.concept import Concept
from ..build_context import BuildContext

OutputFormatter = Callable[[ir.Table], ir.Table]


def _person_subset(ctx: BuildContext, columns: list[str]) -> ir.Table:
    person = ctx.table("person")
    missing = [col for col in columns if col not in person.columns]
    if missing:
        raise ValueError(f"Person table missing required columns: {missing}")
    return person.select(columns)


def standardize_output(
    table: ir.Table,
    *,
    primary_key: str,
    start_column: str,
    end_column: str,
) -> ir.Table:
    """Project and rename columns to the strict builder output contract."""
    start_expr = table[start_column].cast("timestamp")
    same_column = end_column == start_column
    if same_column:
        end_expr = start_expr
        needs_offset = ibis.literal(True)
    elif end_column in table.columns:
        end_raw = table[end_column].cast("timestamp")
        end_expr = ibis.coalesce(end_raw, start_expr).cast("timestamp")
        needs_offset = end_raw.isnull()
    else:
        end_expr = start_expr
        needs_offset = ibis.literal(True)
    one_day = ibis.interval(days=1)
    end_expr = ibis.ifelse(needs_offset, cast(Any, end_expr) + one_day, end_expr).cast(
        "timestamp"
    )
    visit_expr = (
        table.visit_occurrence_id.cast("int64")
        if "visit_occurrence_id" in table.columns
        else ibis.null().cast("int64")
    ).name("visit_occurrence_id")
    return table.select(
        table.person_id.cast("int64").name("person_id"),
        table[primary_key].cast("int64").name("event_id"),
        start_expr.name("start_date"),
        end_expr.name("end_date"),
        visit_expr,
    )


def project_event_columns(
    table: ir.Table,
    *,
    primary_key: str,
    start_column: str,
    end_column: str,
    include_visit_occurrence: bool = False,
) -> ir.Table:
    keep = ["person_id", primary_key, start_column]
    if (
        end_column in table.columns
        or include_visit_occurrence
        and start_column != end_column
    ):
        keep.append(end_column)
    if include_visit_occurrence and "visit_occurrence_id" in table.columns:
        keep.append("visit_occurrence_id")
    unique_keep = [
        col
        for i, col in enumerate(keep)
        if col in table.columns and col not in keep[:i]
    ]
    return table.select(*(table[col] for col in unique_keep))


def apply_codeset_filter(
    table: ir.Table,
    concept_column: str,
    codeset_id: Optional[int],
    ctx: BuildContext,
) -> ir.Table:
    if codeset_id is None:
        return table
    base_columns = table.columns
    left = table.view()
    concepts = ctx.codesets.filter(
        ctx.codesets["codeset_id"] == ibis.literal(codeset_id)
    ).view()
    joined = left.join(concepts, [left[concept_column] == concepts["concept_id"]])
    return _project_columns(joined, base_columns)


def apply_concept_set_selection(
    table: ir.Table,
    column: str,
    selection: Optional[ConceptSetSelection],
    ctx: BuildContext,
) -> ir.Table:
    if selection is None or selection.codeset_id is None:
        return table
    base_columns = table.columns
    left = table.view()
    codeset_table = ctx.codesets.filter(
        ctx.codesets["codeset_id"] == ibis.literal(selection.codeset_id)
    ).view()
    if selection.is_exclusion:
        return left.anti_join(codeset_table, [left[column] == codeset_table.concept_id])
    joined = left.join(codeset_table, [left[column] == codeset_table.concept_id])
    return _project_columns(joined, base_columns)


def coerce_concept_set_selection(
    value: object | None,
) -> Optional[ConceptSetSelection]:
    if value is None:
        return None
    if isinstance(value, ConceptSetSelection):
        return value
    if hasattr(value, "codeset_id"):
        return cast(ConceptSetSelection, value)
    try:
        return ConceptSetSelection(CodesetId=int(cast(Any, value)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Unsupported concept set selection value: {value!r}") from exc


def apply_concept_criteria(
    table: ir.Table,
    *,
    column: str,
    concepts: Sequence[Concept] | None,
    selection: Optional[ConceptSetSelection],
    ctx: BuildContext,
    exclude: bool = False,
) -> ir.Table:
    table = apply_concept_filters(table, column, concepts, exclude=exclude)
    return apply_concept_set_selection(table, column, selection, ctx)


def apply_date_range(
    table: ir.Table, column: str, date_range: Optional[DateRange]
) -> ir.Table:
    if not date_range:
        return table
    expr = table[column]
    if date_range.op.endswith("bt"):
        lower = ibis.literal(date_range.value)
        upper = ibis.literal(date_range.extent)
        predicate = expr.between(lower, upper)
        if date_range.op.startswith("!"):
            predicate = ~predicate
    else:
        comparator = _map_operator(date_range.op)
        operand = ibis.literal(date_range.value)
        predicate = comparator(expr, operand)
    return table.filter(predicate)


def apply_numeric_range(
    table: ir.Table, column, numeric_range: Optional[NumericRange]
) -> ir.Table:
    if not numeric_range or numeric_range.value is None:
        return table
    op = numeric_range.op or "eq"

    expr = table[column] if isinstance(column, str) else column
    if op.endswith("bt"):
        lower = ibis.literal(numeric_range.value)
        upper = ibis.literal(numeric_range.extent)
        predicate = expr.between(lower, upper)
        if op.startswith("!"):
            predicate = ~predicate
    else:
        comparator = _map_operator(op)
        operand = ibis.literal(numeric_range.value)
        predicate = comparator(expr, operand)
    return table.filter(predicate)


def apply_text_filter(
    table: ir.Table, column: str, text_filter: Optional[TextFilter]
) -> ir.Table:
    if not text_filter or not text_filter.text:
        return table
    op = text_filter.op or "contains"
    negate = op.startswith("!")
    core = op[1:] if negate else op
    core = core.lower()
    prefix = "%" if core in {"endswith", "contains"} else ""
    suffix = "%" if core in {"startswith", "contains"} else ""
    pattern = f"{prefix}{text_filter.text}{suffix}"
    col_expr = cast(ir.StringValue, table[column])
    predicate = col_expr.like(pattern)
    if negate:
        predicate = ~predicate
    return table.filter(predicate)


def apply_interval_range(
    table: ir.Table,
    start_column: str,
    end_column: str,
    interval_range: Optional[NumericRange],
) -> ir.Table:
    if not interval_range or interval_range.value is None:
        return table

    op = (interval_range.op or "gte").lower()
    value = int(interval_range.value)
    start = cast(Any, table[start_column])
    end = table[end_column]

    def _interval(days: int):
        return ibis.interval(days=int(days))

    if op.endswith("bt"):
        if interval_range.extent is None:
            raise ValueError("Between operator for interval range requires an extent")
        lower = _interval(value)
        upper = _interval(int(interval_range.extent))
        predicate = (end >= start + lower) & (end <= start + upper)
        if op.startswith("!"):
            predicate = ~predicate
        return table.filter(predicate)

    target = _interval(value)
    if op == "lt":
        predicate = end < start + target
    elif op == "lte":
        predicate = end <= start + target
    elif op == "gt":
        predicate = end > start + target
    elif op == "gte":
        predicate = end >= start + target
    elif op == "eq":
        predicate = (end >= start + target) & (end < start + _interval(value + 1))
    elif op == "!eq":
        predicate = ~((end >= start + target) & (end < start + _interval(value + 1)))
    else:
        raise ValueError(f"Unsupported operator for interval range: {op}")

    return table.filter(predicate)


def _map_operator(op: str):
    mapping = {
        "lt": lambda a, b: a < b,
        "lte": lambda a, b: a <= b,
        "eq": lambda a, b: a == b,
        "!eq": lambda a, b: a != b,
        "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b,
    }
    if op not in mapping:
        raise ValueError(f"Operator {op} not supported")
    return mapping[op]


def apply_concept_filters(
    table: ir.Table,
    column: str,
    include_concepts: Sequence[Concept] | None,
    exclude: bool = False,
) -> ir.Table:
    if not include_concepts:
        return table
    concept_ids = [c.concept_id for c in include_concepts if c.concept_id is not None]
    if not concept_ids:
        return table
    predicate = table[column].isin(cast(Any, concept_ids))
    if exclude:
        predicate = ~predicate
    return table.filter(predicate)


def apply_age_filter(
    table: ir.Table,
    age_range: Optional[NumericRange],
    ctx: BuildContext,
    start_column: str,
) -> ir.Table:
    if not age_range:
        return table
    base_columns = table.columns
    person = _person_subset(ctx, ["person_id", "year_of_birth"])
    joined = table.join(person, ["person_id"])
    start_expr = cast(ir.TimestampValue, _ensure_timestamp(joined[start_column]))
    age_expr = start_expr.year() - cast(Any, joined.year_of_birth)
    joined = joined.mutate(_criteria_age=age_expr)
    filtered = apply_numeric_range(joined, "_criteria_age", age_range)
    filtered = filtered.drop("_criteria_age")
    return _project_columns(filtered, base_columns)


def apply_gender_filter(
    table: ir.Table,
    genders: list[Concept] | None,
    gender_selection: Optional[ConceptSetSelection],
    ctx: BuildContext,
) -> ir.Table:
    return _apply_person_concept_filter(
        table,
        person_column="gender_concept_id",
        concepts=genders,
        selection=gender_selection,
        ctx=ctx,
    )


def apply_race_filter(
    table: ir.Table,
    races: list[Concept] | None,
    race_selection: Optional[ConceptSetSelection],
    ctx: BuildContext,
) -> ir.Table:
    return _apply_person_concept_filter(
        table,
        person_column="race_concept_id",
        concepts=races,
        selection=race_selection,
        ctx=ctx,
    )


def apply_ethnicity_filter(
    table: ir.Table,
    ethnicities: list[Concept] | None,
    ethnicity_selection: Optional[ConceptSetSelection],
    ctx: BuildContext,
) -> ir.Table:
    return _apply_person_concept_filter(
        table,
        person_column="ethnicity_concept_id",
        concepts=ethnicities,
        selection=ethnicity_selection,
        ctx=ctx,
    )


def _apply_person_concept_filter(
    table: ir.Table,
    *,
    person_column: str,
    concepts: Sequence[Concept] | None,
    selection: Optional[ConceptSetSelection],
    ctx: BuildContext,
) -> ir.Table:
    if not concepts and not selection:
        return table
    base_columns = table.columns
    person = _person_subset(ctx, ["person_id", person_column])
    joined = table.join(person, ["person_id"])
    joined = apply_concept_criteria(
        joined,
        column=person_column,
        concepts=concepts,
        selection=selection,
        ctx=ctx,
    )
    return _project_columns(joined, base_columns)


def apply_observation_window(
    events: ir.Table,
    observation_window,
    ctx: BuildContext,
) -> ir.Table:
    if observation_window is None:
        return events
    observation = ctx.table("observation_period").select(
        "person_id", "observation_period_start_date", "observation_period_end_date"
    )
    # Use a view to ensure subsequent joins don't mix incompatible relations.
    left = events.view()
    joined = left.join(observation, ["person_id"])
    prior_days = ibis.interval(days=int(observation_window.prior_days or 0))
    post_days = ibis.interval(days=int(observation_window.post_days or 0))
    start_col = _ensure_timestamp(joined.observation_period_start_date)
    end_col = _ensure_timestamp(joined.observation_period_end_date)
    start_bound = start_col + cast(Any, prior_days)
    end_bound = end_col - cast(Any, post_days)
    filtered = joined.filter(
        (joined.start_date >= start_bound) & (joined.start_date <= end_bound)
    )
    base_projection = [filtered[col] for col in events.columns]
    base_projection.extend(
        filtered[col]
        for col in ("observation_period_start_date", "observation_period_end_date")
        if col in filtered.columns
    )
    return filtered.select(*base_projection)


def apply_first_event(table: ir.Table, start_column: str, primary_key: str) -> ir.Table:
    window = ibis.window(
        group_by=table.person_id,
        order_by=[table[start_column], table[primary_key]],
    )

    ranked = table.mutate(_row_num=row_number().over(window))
    filtered = ranked.filter(ranked["_row_num"] == ibis.literal(0))
    keep_columns = [col for col in table.columns if col != "_row_num"]
    if keep_columns:
        return filtered.select(*(filtered[col] for col in keep_columns))
    return filtered.drop("_row_num")


def apply_visit_concept_filters(
    table: ir.Table,
    visit_types: list[Concept] | None,
    visit_selection: Optional[ConceptSetSelection],
    ctx: BuildContext,
) -> ir.Table:
    return apply_concept_criteria(
        table,
        column="visit_concept_id",
        concepts=visit_types,
        selection=visit_selection,
        ctx=ctx,
    )


def apply_provider_specialty_filter(
    table: ir.Table,
    provider_specialties: list[Concept] | None,
    provider_specialty_selection: Optional[ConceptSetSelection],
    ctx: BuildContext,
    provider_column: str = "provider_id",
) -> ir.Table:
    if not provider_specialties and not provider_specialty_selection:
        return table
    provider = ctx.table("provider")
    provider = apply_concept_criteria(
        provider,
        column="specialty_concept_id",
        concepts=provider_specialties,
        selection=provider_specialty_selection,
        ctx=ctx,
    )
    filtered = provider.select(provider.provider_id)
    return table.semi_join(filtered, [table[provider_column] == filtered.provider_id])


def apply_care_site_filter(
    table: ir.Table,
    place_of_service_selection: Optional[ConceptSetSelection],
    ctx: BuildContext,
    care_site_column: str = "care_site_id",
) -> ir.Table:
    if not place_of_service_selection:
        return table
    care_site = ctx.table("care_site")
    filtered = apply_concept_set_selection(
        care_site, "place_of_service_concept_id", place_of_service_selection, ctx
    )
    filtered = filtered.select(filtered.care_site_id)
    return table.semi_join(filtered, [table[care_site_column] == filtered.care_site_id])


def apply_location_region_filter(
    table: ir.Table,
    *,
    care_site_column: str,
    location_codeset_id: Optional[int],
    start_column: str,
    end_column: str,
    ctx: BuildContext,
) -> ir.Table:
    if not location_codeset_id:
        return table
    base_columns = table.columns
    care_site = ctx.table("care_site")
    location_history = ctx.table("location_history")
    location = ctx.table("location")
    joined = table.join(care_site, [table[care_site_column] == care_site.care_site_id])
    start_expr = _ensure_timestamp(joined[start_column])
    end_expr = _ensure_timestamp(joined[end_column])
    lh = location_history
    lh_condition = (
        (joined[care_site_column] == lh.entity_id)
        & (lh.domain_id == ibis.literal("CARE_SITE"))
        & (start_expr >= lh.start_date)
        & (
            end_expr
            <= ibis.coalesce(lh.end_date, ibis.literal("2099-12-31").cast("date"))
        )
    )
    joined = joined.join(lh, [lh_condition])
    joined = joined.join(location, [joined.location_id == location.location_id])
    codeset = ctx.codesets.filter(
        ctx.codesets.codeset_id == ibis.literal(location_codeset_id)
    )
    filtered = joined.join(codeset, [location.region_concept_id == codeset.concept_id])
    return _project_columns(filtered, base_columns)


def apply_user_defined_period(
    table: ir.Table,
    start_column: str,
    end_column: str,
    period,
) -> tuple[ir.Table, str, str]:
    if not period:
        return table, start_column, end_column

    base_start = table[start_column]
    base_end = table[end_column]
    additions = {}
    new_start = start_column
    new_end = end_column

    if getattr(period, "start_date", None):
        literal = _literal_like(period.start_date, base_start)
        additions["_user_defined_start"] = literal
        table = table.filter((base_start <= literal) & (base_end >= literal))
        new_start = "_user_defined_start"

    if getattr(period, "end_date", None):
        literal = _literal_like(period.end_date, base_end)
        additions["_user_defined_end"] = literal
        table = table.filter((base_start <= literal) & (base_end >= literal))
        new_end = "_user_defined_end"

    if additions:
        table = table.mutate(**additions)

    return table, new_start, new_end


def _literal_like(value, reference):
    literal = ibis.literal(value)
    dtype = reference.type()
    if dtype.is_timestamp():
        return literal.cast("timestamp")
    if dtype.is_date():
        return literal.cast("date")
    return literal


def _ensure_timestamp(expr: ir.Value) -> ir.Value:
    dtype = expr.type()
    if dtype.is_timestamp():
        return expr
    if dtype.is_date():
        return expr.cast("timestamp")
    if dtype.is_string():
        return ibis.to_timestamp(expr)
    raise ValueError(f"Cannot convert expression of type {dtype} to timestamp")


def _cast_like(expr: ir.Value, reference: ir.Value) -> ir.Value:
    target_type = reference.type()
    if expr.type() == target_type:
        return expr
    return expr.cast(cast(Any, target_type))


def _project_columns(table: ir.Table, column_names: Sequence[str]) -> ir.Table:
    available = [name for name in column_names if name in table.columns]
    if not available:
        return table
    return table.select(*[table[name] for name in available])


def apply_end_strategy(
    events: ir.Table,
    strategy: Optional[EndStrategy | DateOffsetStrategy | CustomEraStrategy],
    ctx: BuildContext,
) -> ir.Table:
    date_offset, custom_era = _resolve_end_strategy_parts(strategy)
    if not date_offset and not custom_era:
        if "observation_period_end_date" in events.columns:
            op_end = _cast_like(
                _ensure_timestamp(events.observation_period_end_date), events.end_date
            )
            return events.mutate(end_date=op_end)
        return events
    result = events
    if custom_era:
        result = _apply_custom_era_strategy(result, custom_era, ctx)
    if date_offset:
        interval = ibis.interval(days=int(date_offset.offset))
        date_field = str(date_offset.date_field or "StartDate").lower()
        anchor = (
            _ensure_timestamp(result.start_date)
            if date_field == "startdate"
            else _ensure_timestamp(result.end_date)
        )
        shifted = anchor + cast(Any, interval)
        if "observation_period_end_date" in result.columns:
            shifted = ibis.least(
                shifted,
                _ensure_timestamp(result.observation_period_end_date),
            )
        result = result.mutate(end_date=_cast_like(shifted, result.end_date))
    return result


def has_end_strategy(
    strategy: Optional[EndStrategy | DateOffsetStrategy | CustomEraStrategy],
) -> bool:
    date_offset, custom_era = _resolve_end_strategy_parts(strategy)
    return bool(date_offset or custom_era)


def _resolve_end_strategy_parts(
    strategy: Optional[EndStrategy | DateOffsetStrategy | CustomEraStrategy],
) -> tuple[Optional[DateOffsetStrategy], Optional[CustomEraStrategy]]:
    if strategy is None:
        return None, None

    if isinstance(strategy, DateOffsetStrategy):
        return strategy, None

    if isinstance(strategy, CustomEraStrategy):
        return None, strategy

    date_offset = getattr(strategy, "date_offset", None)
    custom_era = getattr(strategy, "custom_era", None)

    if isinstance(date_offset, dict):
        date_offset = DateOffsetStrategy.model_validate(date_offset, strict=False)
    if isinstance(custom_era, dict):
        custom_era = CustomEraStrategy.model_validate(custom_era, strict=False)

    return date_offset, custom_era


def collapse_events(events: ir.Table, settings: CollapseSettings | None) -> ir.Table:
    if not settings or settings.collapse_type != CollapseType.ERA:
        return events
    pad_interval = ibis.interval(days=int(settings.era_pad or 0))
    order_by = [events.start_date, events.end_date, events.event_id]
    prev_window = ibis.window(
        group_by=events.person_id,
        order_by=order_by,
        preceding=(None, 1),
    )
    extended_end = events.end_date + cast(Any, pad_interval)
    prev_max = extended_end.max().over(prev_window)
    is_start = ibis.ifelse(
        prev_max.notnull() & (prev_max >= events.start_date),
        0,
        1,
    )
    annotated = events.mutate(
        extended_end=extended_end,
        is_start=is_start,
    )
    is_start_col = cast(ir.IntegerColumn, annotated["is_start"])
    era_window = ibis.window(
        group_by=annotated.person_id,
        order_by=[
            annotated.start_date,
            ibis.desc(is_start_col),
            annotated.end_date,
            annotated.event_id,
        ],
    )
    era_id = is_start_col.cumsum().over(era_window)
    grouped = annotated.mutate(_era_id=era_id)
    max_end = cast(ir.IntervalScalar, grouped.extended_end.max())
    collapsed = grouped.group_by(grouped.person_id, grouped._era_id).aggregate(
        start_date=grouped.start_date.min(),
        end_date=(max_end - pad_interval),
        visit_occurrence_id=grouped.visit_occurrence_id.max(),
    )
    final_window = ibis.window(
        order_by=[collapsed.person_id, collapsed.start_date, collapsed.end_date]
    )
    collapsed = collapsed.mutate(
        event_id=(ibis.row_number().over(final_window) + 1)
    ).select("person_id", "event_id", "start_date", "end_date", "visit_occurrence_id")
    return collapsed


def _apply_custom_era_strategy(
    events: ir.Table, strategy: CustomEraStrategy, ctx: BuildContext
) -> ir.Table:
    if strategy.drug_codeset_id is None:
        raise ValueError("Custom era strategy requires a drug codeset id.")

    persons = events.select(events.person_id).distinct()
    codeset = ctx.codesets.filter(ctx.codesets.codeset_id == strategy.drug_codeset_id)
    drug_exposure = ctx.table("drug_exposure")

    def _exposure_query(concept_column: str) -> ir.Table:
        return (
            drug_exposure.join(persons, ["person_id"])
            .join(codeset, drug_exposure[concept_column] == codeset.concept_id)
            .select(
                drug_exposure.person_id,
                drug_exposure.drug_exposure_start_date.name("drug_exposure_start_date"),
                _drug_exposure_end(drug_exposure, strategy).name(
                    "drug_exposure_end_date"
                ),
            )
        )

    exposures = _exposure_query("drug_concept_id").union(
        _exposure_query("drug_source_concept_id"), distinct=False
    )

    gap = int(strategy.gap_days or 0)
    offset = int(strategy.offset or 0)
    extend_interval = ibis.interval(days=gap + offset)

    dt = exposures.select(
        exposures.person_id,
        exposures.drug_exposure_start_date.name("start_date"),
        (exposures.drug_exposure_end_date + extend_interval).name("extended_end"),
    ).distinct()

    prev_max_window = ibis.window(
        group_by=dt.person_id,
        order_by=[dt.start_date, dt.extended_end],
        preceding=(None, 1),
    )
    prev_running_max = dt.extended_end.max().over(prev_max_window)
    is_start = ibis.ifelse(
        prev_running_max.notnull() & (prev_running_max >= dt.start_date), 0, 1
    )
    staged = dt.mutate(is_start=is_start).view()
    cumsum_window = ibis.window(
        group_by=staged.person_id, order_by=[staged.start_date, staged.extended_end]
    )
    group_idx = staged.is_start.cumsum().over(cumsum_window)
    annotated = staged.mutate(group_idx=group_idx)

    eras = annotated.group_by(annotated.person_id, annotated.group_idx).aggregate(
        era_start=annotated.start_date.min(),
        era_end=(annotated.extended_end.max() - ibis.interval(days=gap)),
    )

    join_condition = (
        (events.person_id == eras.person_id)
        & (events.start_date >= eras.era_start)
        & (events.start_date <= eras.era_end)
    )
    joined = events.join(eras, join_condition, how="inner")
    if not joined.columns:
        return events.limit(0)
    supplemental = [
        joined[column]
        for column in ("observation_period_start_date", "observation_period_end_date")
        if column in joined.columns
    ]
    return joined.select(
        joined.person_id,
        joined.event_id,
        joined.start_date,
        joined.era_end.name("end_date"),
        joined.visit_occurrence_id,
        *supplemental,
    )


def _drug_exposure_end(
    drug_exposure: ir.Table, strategy: CustomEraStrategy
) -> ir.Value:
    start = drug_exposure.drug_exposure_start_date
    if strategy.days_supply_override is not None:
        return start + ibis.interval(days=int(strategy.days_supply_override))

    end_candidates = [
        drug_exposure.drug_exposure_end_date,
        ibis.ifelse(
            drug_exposure.days_supply.notnull(),
            start + (ibis.interval(days=1) * drug_exposure.days_supply.cast("int64")),
            ibis.null(),
        ),
        start + ibis.interval(days=1),
    ]
    return ibis.coalesce(*end_candidates)
