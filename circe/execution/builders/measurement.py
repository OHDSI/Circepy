from __future__ import annotations

import ibis

from ...cohortdefinition.criteria import Measurement
from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_codeset_filter,
    apply_concept_criteria,
    apply_date_range,
    apply_first_event,
    apply_gender_filter,
    apply_numeric_range,
    apply_provider_specialty_filter,
    apply_visit_concept_filters,
    standardize_output,
)
from .groups import apply_criteria_group
from .registry import register


@register("Measurement")
def build_measurement(criteria: Measurement, ctx: BuildContext):
    table = ctx.table("measurement")
    concept_column = criteria.get_concept_id_column()
    table = apply_codeset_filter(table, concept_column, criteria.codeset_id, ctx)
    if criteria.first:
        table = apply_first_event(
            table, criteria.get_start_date_column(), criteria.get_primary_key_column()
        )

    table = apply_date_range(
        table, criteria.get_start_date_column(), criteria.occurrence_start_date
    )
    table = apply_date_range(
        table, criteria.get_end_date_column(), criteria.occurrence_end_date
    )

    table = apply_concept_criteria(
        table,
        column="measurement_type_concept_id",
        concepts=criteria.measurement_type,
        selection=criteria.measurement_type_cs,
        ctx=ctx,
        exclude=bool(criteria.measurement_type_exclude),
    )

    table = apply_concept_criteria(
        table,
        column="operator_concept_id",
        concepts=getattr(criteria, "operator_concept", None),
        selection=getattr(criteria, "operator_concept_cs", None),
        ctx=ctx,
    )

    value_column = "value_as_number"
    if criteria.unit:
        table = apply_concept_criteria(
            table,
            column="unit_concept_id",
            concepts=criteria.unit,
            selection=None,
            ctx=ctx,
        )
        table, value_column = _maybe_normalize_units(
            table, criteria.unit, criteria.value_as_number
        )
    table = apply_concept_criteria(
        table,
        column="unit_concept_id",
        concepts=None,
        selection=criteria.unit_cs,
        ctx=ctx,
    )

    table = apply_concept_criteria(
        table,
        column="value_as_concept_id",
        concepts=criteria.value_as_concept,
        selection=criteria.value_as_concept_cs,
        ctx=ctx,
    )

    table = apply_numeric_range(table, value_column, criteria.value_as_number)
    table = apply_numeric_range(table, "range_low", criteria.range_low)
    table = apply_numeric_range(table, "range_high", criteria.range_high)
    if getattr(criteria, "range_low_ratio", None):
        denom = ibis.ifelse(table.range_low == 0, ibis.null(), table.range_low)
        ratio = (table.value_as_number / denom).name("_range_low_ratio")
        table = table.mutate(_range_low_ratio=ratio)
        table = apply_numeric_range(table, "_range_low_ratio", criteria.range_low_ratio)
    if getattr(criteria, "range_high_ratio", None):
        denom = ibis.ifelse(table.range_high == 0, ibis.null(), table.range_high)
        ratio = (table.value_as_number / denom).name("_range_high_ratio")
        table = table.mutate(_range_high_ratio=ratio)
        table = apply_numeric_range(
            table, "_range_high_ratio", criteria.range_high_ratio
        )

    if getattr(criteria, "abnormal", None):
        abnormal_predicate = (
            (table.value_as_number < table.range_low)
            | (table.value_as_number > table.range_high)
            | table.value_as_concept_id.isin([4155142, 4155143])
        )
        table = table.filter(abnormal_predicate)

    if criteria.age:
        table = apply_age_filter(
            table, criteria.age, ctx, criteria.get_start_date_column()
        )
    table = apply_gender_filter(table, criteria.gender, criteria.gender_cs, ctx)
    table = apply_provider_specialty_filter(
        table,
        getattr(criteria, "provider_specialty", None),
        getattr(criteria, "provider_specialty_cs", None),
        ctx,
        provider_column="provider_id",
    )
    table = apply_visit_concept_filters(
        table, criteria.visit_type, criteria.visit_type_cs, ctx
    )
    if criteria.measurement_source_concept is not None:
        table = apply_codeset_filter(
            table,
            "measurement_source_concept_id",
            criteria.measurement_source_concept,
            ctx,
        )

    events = standardize_output(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)


def _maybe_normalize_units(table, units, value_range):
    """
    Best-effort unit normalization for numeric comparisons.

    Circe generally relies on unit-specific criteria rows (separate thresholds per unit scale).
    Normalizing in that situation breaks parity (e.g. neutrophil counts expressed as 10..1500 cells/uL).

    Strategy:
      - Always normalize mass to kilograms (pounds -> kg).
      - For cell counts, only normalize when the numeric range appears to be in the canonical 10^9/L scale.
        Heuristic: upper bound <= 100.
    """
    unit_ids = [
        concept.concept_id for concept in units if concept.concept_id is not None
    ]
    if not unit_ids:
        return table, "value_as_number"
    if not all(unit_id in _UNIT_NORMALIZATION for unit_id in unit_ids):
        return table, "value_as_number"
    groups = {_UNIT_NORMALIZATION[unit_id][0] for unit_id in unit_ids}
    if len(groups) != 1:
        return table, "value_as_number"

    group = next(iter(groups))
    if group == "mass_kg":
        should_normalize = True
    elif group == "count_10e9_per_l":
        should_normalize = _range_looks_like_canonical_cell_count(value_range)
    else:
        should_normalize = False

    if not should_normalize:
        return table, "value_as_number"

    multiplier = _unit_multiplier_expr(table.unit_concept_id, unit_ids)
    normalized = (table.value_as_number * multiplier).name("_normalized_value")
    table = table.mutate(_normalized_value=normalized)
    return table, "_normalized_value"


def _range_looks_like_canonical_cell_count(value_range) -> bool:
    if value_range is None or value_range.value is None:
        return False
    op = (value_range.op or "eq").lower()
    upper = float(value_range.value)
    if op.endswith("bt") and value_range.extent is not None:
        upper = max(upper, float(value_range.extent))
    # Canonical 10^9/L scale is typically << 100; high thresholds indicate raw unit ranges.
    return upper <= 100.0


def _unit_multiplier_expr(unit_column, unit_ids):
    multiplier_expr = ibis.literal(1.0)
    for unit_id in unit_ids:
        multiplier = _UNIT_NORMALIZATION[unit_id][1]
        multiplier_expr = ibis.ifelse(
            unit_column == ibis.literal(unit_id),
            ibis.literal(multiplier),
            multiplier_expr,
        )
    return multiplier_expr


_UNIT_NORMALIZATION = {
    # Mass
    9529: ("mass_kg", 1.0),  # kilogram
    3195625: ("mass_kg", 0.45359237),  # pound
    # Cell counts per liter (expressed in 10^9/L)
    9444: ("count_10e9_per_l", 1.0),  # billion per liter
    44777588: ("count_10e9_per_l", 1.0),
    8848: ("count_10e9_per_l", 1.0),  # thousand per microliter
    8816: ("count_10e9_per_l", 1.0),  # million per milliliter
    8961: ("count_10e9_per_l", 1.0),  # thousand per cubic millimeter
    8784: ("count_10e9_per_l", 0.001),  # cells per microliter
    8647: ("count_10e9_per_l", 0.001),  # per microliter
}
