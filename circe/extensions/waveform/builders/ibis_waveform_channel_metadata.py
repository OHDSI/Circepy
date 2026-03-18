"""Ibis execution builder for WaveformChannelMetadata criteria."""

from __future__ import annotations

from circe.execution.build_context import BuildContext
from circe.execution.builders.common import (
    apply_concept_filters,
    apply_numeric_range,
    apply_text_filter,
    standardize_output,
)
from circe.execution.builders.groups import apply_criteria_group
from circe.extensions import ibis_builder

from ..criteria import WaveformChannelMetadata


@ibis_builder("WaveformChannelMetadata")
def build_waveform_channel_metadata(criteria: WaveformChannelMetadata, ctx: BuildContext):
    """Build an ibis event table from waveform_channel_metadata.

    Channel metadata rows have no timestamps of their own; start_date/end_date
    are sourced from the parent waveform_registry file bounds via a join.
    person_id is resolved through the registry → occurrence chain.
    """
    table = ctx.table("waveform_channel_metadata")

    # Join waveform_registry to get file dates and occurrence link
    registry = ctx.table("waveform_registry").select(
        "waveform_registry_id",
        "waveform_occurrence_id",
        "file_start_datetime",
        "file_end_datetime",
    )
    table = table.join(
        registry,
        table.waveform_registry_id == registry.waveform_registry_id,
    )

    # Join waveform_occurrence to get person_id and visit context
    occurrence = ctx.table("waveform_occurrence").select(
        "waveform_occurrence_id",
        "person_id",
        "visit_occurrence_id",
    )
    table = table.join(
        occurrence,
        table.waveform_occurrence_id == occurrence.waveform_occurrence_id,
    )

    # Registry link filter
    table = apply_numeric_range(table, "waveform_registry_id", criteria.waveform_registry_id)

    # Channel identification
    if criteria.channel_concept_id:
        table = apply_concept_filters(table, "channel_concept_id", criteria.channel_concept_id)
    table = apply_text_filter(table, "waveform_channel_source_value", criteria.waveform_channel_source_value)

    # Metadata type
    if criteria.metadata_concept_id:
        table = apply_concept_filters(table, "metadata_concept_id", criteria.metadata_concept_id)
    table = apply_text_filter(table, "metadata_source_value", criteria.metadata_source_value)

    # Metadata values
    table = apply_numeric_range(table, "value_as_number", criteria.value_as_number)
    if criteria.value_as_concept_id:
        table = apply_concept_filters(table, "value_as_concept_id", criteria.value_as_concept_id)

    # Units
    if criteria.unit_concept_id:
        table = apply_concept_filters(table, "unit_concept_id", criteria.unit_concept_id)

    # Device / procedure linkage
    table = apply_numeric_range(table, "device_exposure_id", criteria.device_exposure_id)
    table = apply_numeric_range(table, "procedure_occurrence_id", criteria.procedure_occurrence_id)

    events = standardize_output(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
