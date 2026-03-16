"""Ibis execution builder for WaveformOccurrence criteria."""
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

from ..criteria import WaveformOccurrence


@ibis_builder("WaveformOccurrence")
def build_waveform_occurrence(criteria: WaveformOccurrence, ctx: BuildContext):
    """Build an ibis event table from waveform_occurrence.

    Output columns match the standard pipeline contract:
    person_id, event_id, start_date, end_date, visit_occurrence_id.
    """
    table = ctx.table("waveform_occurrence")

    # Concept filter
    if criteria.waveform_occurrence_concept_id:
        table = apply_concept_filters(
            table,
            "waveform_occurrence_concept_id",
            criteria.waveform_occurrence_concept_id,
        )

    # Temporal bounds
    table = apply_date_range(
        table,
        "waveform_occurrence_start_datetime",
        criteria.occurrence_start_datetime,
    )
    table = apply_date_range(
        table,
        "waveform_occurrence_end_datetime",
        criteria.occurrence_end_datetime,
    )

    # Visit context
    table = apply_numeric_range(table, "visit_occurrence_id", criteria.visit_occurrence_id)
    table = apply_numeric_range(table, "visit_detail_id", criteria.visit_detail_id)

    # File count
    table = apply_numeric_range(table, "num_of_files", criteria.num_of_files)

    # Source value text filter
    table = apply_text_filter(
        table,
        "waveform_occurrence_source_value",
        criteria.waveform_occurrence_source_value,
    )

    # Sequence/chain filtering
    table = apply_numeric_range(
        table,
        "preceding_waveform_occurrence_id",
        criteria.preceding_waveform_occurrence_id,
    )

    events = standardize_output(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)

