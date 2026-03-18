"""Ibis execution builder for WaveformFeature criteria."""

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

from ..criteria import WaveformFeature


@ibis_builder("WaveformFeature")
def build_waveform_feature(criteria: WaveformFeature, ctx: BuildContext):
    """Build an ibis event table from waveform_feature.

    waveform_feature stores derived measurements (heart rate, SpO2, arrhythmia
    detections, AI embeddings, etc.).  person_id and visit_occurrence_id are
    resolved by joining to waveform_occurrence.
    """
    table = ctx.table("waveform_feature")

    # Join waveform_occurrence to obtain person_id and visit context
    occurrence = ctx.table("waveform_occurrence").select(
        "waveform_occurrence_id",
        "person_id",
        "visit_occurrence_id",
    )
    table = table.join(
        occurrence,
        table.waveform_occurrence_id == occurrence.waveform_occurrence_id,
    )

    # Parent link filters
    table = apply_numeric_range(table, "waveform_occurrence_id", criteria.waveform_occurrence_id)
    table = apply_numeric_range(table, "waveform_registry_id", criteria.waveform_registry_id)
    table = apply_numeric_range(table, "waveform_channel_metadata_id", criteria.waveform_channel_metadata_id)

    # Feature type (e.g., heart rate, SpO2, QRS)
    if criteria.feature_concept_id:
        table = apply_concept_filters(table, "feature_concept_id", criteria.feature_concept_id)

    # Algorithm used to derive feature
    if criteria.algorithm_concept_id:
        table = apply_concept_filters(table, "algorithm_concept_id", criteria.algorithm_concept_id)
    table = apply_text_filter(table, "algorithm_source_value", criteria.algorithm_source_value)

    # Temporal window for feature
    table = apply_date_range(table, "waveform_feature_start_timestamp", criteria.feature_start_timestamp)
    table = apply_date_range(table, "waveform_feature_end_timestamp", criteria.feature_end_timestamp)

    # Feature values
    table = apply_numeric_range(table, "value_as_number", criteria.value_as_number)
    if criteria.value_as_concept_id:
        table = apply_concept_filters(table, "value_as_concept_id", criteria.value_as_concept_id)

    # Units
    if criteria.unit_concept_id:
        table = apply_concept_filters(table, "unit_concept_id", criteria.unit_concept_id)

    # Links to standard OMOP tables
    table = apply_numeric_range(table, "measurement_id", criteria.measurement_id)
    table = apply_numeric_range(table, "observation_id", criteria.observation_id)

    events = standardize_output(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
