from __future__ import annotations

from typing import Any, Optional

import ibis.expr.types as ir

from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_codeset_filter,
    apply_date_range,
    apply_gender_filter,
    standardize_output,
)
from .groups import apply_criteria_group


def apply_primary_concept_and_date_filters(
    table: ir.Table,
    *,
    ctx: BuildContext,
    concept_column: str,
    codeset_id: Optional[int],
    start_column: str,
    start_range: Any,
    end_column: str,
    end_range: Any,
) -> ir.Table:
    """Apply the common concept + start/end date range filters."""
    table = apply_codeset_filter(table, concept_column, codeset_id, ctx)
    table = apply_date_range(table, start_column, start_range)
    table = apply_date_range(table, end_column, end_range)
    return table


def apply_age_and_gender_filters(
    table: ir.Table,
    *,
    ctx: BuildContext,
    age_column: str,
    age_range: Any = None,
    genders: Any = None,
    gender_selection: Any = None,
) -> ir.Table:
    """Apply age + gender filters with shared ordering."""
    if age_range:
        table = apply_age_filter(table, age_range, ctx, age_column)
    return apply_gender_filter(table, genders, gender_selection, ctx)


def apply_age_at_start_end_filters(
    table: ir.Table,
    *,
    ctx: BuildContext,
    start_column: str,
    end_column: str,
    age_at_start: Any = None,
    age_at_end: Any = None,
) -> ir.Table:
    """Apply optional age-at-start / age-at-end filters."""
    if age_at_start:
        table = apply_age_filter(table, age_at_start, ctx, start_column)
    if age_at_end:
        table = apply_age_filter(table, age_at_end, ctx, end_column)
    return table


def finalize_criteria_events(
    table: ir.Table,
    *,
    criteria: Any,
    ctx: BuildContext,
    primary_key: str,
    start_column: str,
    end_column: str,
) -> ir.Table:
    """Standardize output columns and apply correlated criteria."""
    events = standardize_output(
        table,
        primary_key=primary_key,
        start_column=start_column,
        end_column=end_column,
    )
    return apply_criteria_group(
        events, getattr(criteria, "correlated_criteria", None), ctx
    )
