"""Ibis execution builder for WaveformRegistry criteria."""

from __future__ import annotations

from circe.execution.build_context import BuildContext
from circe.execution.builders.common import (
    apply_concept_filters,
    apply_date_range,
    apply_numeric_range,
    apply_text_filter,
    standardize_output,
)
from circe.execution.builders.groups import apply_criteria_group
from circe.extensions import ibis_builder

from ..criteria import WaveformRegistry


@ibis_builder("WaveformRegistry")
def build_waveform_registry(criteria: WaveformRegistry, ctx: BuildContext):
    """Build an ibis event table from waveform_registry.

    waveform_registry rows have file-level temporal bounds but no person_id
    directly — person_id is carried via the waveform_occurrence join.
    The output follows the standard pipeline contract via standardize_output.
    """
    table = ctx.table("waveform_registry")

    # Join to waveform_occurrence to obtain person_id and visit context.
    occurrence = ctx.table("waveform_occurrence").select(
        "waveform_occurrence_id",
        "person_id",
        "visit_occurrence_id",
    )
    base_columns = list(table.columns) + ["person_id", "visit_occurrence_id"]
    table = table.join(
        occurrence,
        table.waveform_occurrence_id == occurrence.waveform_occurrence_id,
    )
    # Keep only required columns to avoid ambiguity
    keep = [c for c in base_columns if c in table.columns]
    # deduplicate while preserving order
    seen: set[str] = set()
    unique_keep: list[str] = []
    for c in keep:
        if c not in seen:
            seen.add(c)
            unique_keep.append(c)
    table = table.select(unique_keep)

    # Parent occurrence link
    table = apply_numeric_range(table, "waveform_occurrence_id", criteria.waveform_occurrence_id)

    # File temporal bounds
    table = apply_date_range(table, "file_start_datetime", criteria.file_start_datetime)
    table = apply_date_range(table, "file_end_datetime", criteria.file_end_datetime)

    # File format
    if criteria.file_extension_concept_id:
        table = apply_concept_filters(
            table,
            "file_extension_concept_id",
            criteria.file_extension_concept_id,
        )
    table = apply_text_filter(table, "file_extension_source_value", criteria.file_extension_source_value)

    # Visit context (denormalized)
    table = apply_numeric_range(table, "visit_occurrence_id", criteria.visit_occurrence_id)
    table = apply_numeric_range(table, "visit_detail_id", criteria.visit_detail_id)

    events = standardize_output(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
