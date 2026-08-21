from __future__ import annotations

from circe.extensions import lowerer

from ...execution.lower.common import (
    append_concept_filters,
    append_numeric_filter,
    append_text_filter,
    build_standard_domain_plan,
    lower_common_steps,
)
from ...execution.normalize.criteria import NormalizedCriterion
from ...execution.plan.events import EventPlan
from .criteria import WaveformOccurrence


@lowerer(WaveformOccurrence)
def lower_waveform_occurrence(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, WaveformOccurrence):
        raise TypeError("lower_waveform_occurrence requires WaveformOccurrence criteria")

    steps = lower_common_steps(criterion)

    append_concept_filters(
        steps,
        column="waveform_occurrence_concept_id",
        concepts=raw.waveform_occurrence_concept_id,
        # codeset_selection does not exist on WaveformOccurrence based on the pydantic logic, we just pass concepts
    )

    append_text_filter(
        steps, column="waveform_occurrence_source_value", value=raw.waveform_occurrence_source_value
    )

    append_numeric_filter(steps, column="visit_occurrence_id", value=raw.visit_occurrence_id)

    append_numeric_filter(steps, column="visit_detail_id", value=raw.visit_detail_id)

    append_numeric_filter(steps, column="num_of_files", value=raw.num_of_files)

    append_numeric_filter(
        steps, column="preceding_waveform_occurrence_id", value=raw.preceding_waveform_occurrence_id
    )

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
    )
