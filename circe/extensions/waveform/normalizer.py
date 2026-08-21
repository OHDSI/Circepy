from __future__ import annotations

from circe.extensions import normalizer

from ...execution.normalize.criteria import NormalizedCriterion, _build_normalized_criterion
from ...execution.normalize.windows import normalize_date_range
from .criteria import WaveformOccurrence


@normalizer(WaveformOccurrence)
def normalize_waveform_occurrence(criteria: WaveformOccurrence) -> NormalizedCriterion:
    return _build_normalized_criterion(
        criteria=criteria,
        criterion_type="WaveformOccurrence",
        domain="waveform_occurrence",
        source_table="waveform_occurrence",
        event_id_column="waveform_occurrence_id",
        start_date_column="waveform_occurrence_start_datetime",
        end_date_column="waveform_occurrence_end_datetime",
        concept_column="waveform_occurrence_concept_id",
        source_concept_column=None,
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=None,
        first=False,
        occurrence_start_date=normalize_date_range(criteria.occurrence_start_datetime),
        occurrence_end_date=normalize_date_range(criteria.occurrence_end_datetime),
    )
