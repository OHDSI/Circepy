from __future__ import annotations

import ibis

from ..plan.events import EventSource
from ..plan.schema import (
    CONCEPT_ID,
    CRITERION_INDEX,
    CRITERION_TYPE,
    DOMAIN,
    END_DATE,
    EVENT_ID,
    PERSON_ID,
    SOURCE_CONCEPT_ID,
    SOURCE_TABLE,
    STANDARD_EVENT_COLUMNS,
    START_DATE,
    VISIT_OCCURRENCE_ID,
)


def standardize_event_table(
    table,
    *,
    source: EventSource,
    criterion_type: str,
    criterion_index: int,
):
    concept_expr = ibis.null().cast("int64")
    if source.concept_column and source.concept_column in table.columns:
        concept_expr = table[source.concept_column].cast("int64")

    source_concept_expr = ibis.null().cast("int64")
    if source.source_concept_column and source.source_concept_column in table.columns:
        source_concept_expr = table[source.source_concept_column].cast("int64")

    visit_occ_expr = ibis.null().cast("int64")
    if source.visit_occurrence_column and source.visit_occurrence_column in table.columns:
        visit_occ_expr = table[source.visit_occurrence_column].cast("int64")

    standardized = table.select(
        table[source.person_id_column].cast("int64").name(PERSON_ID),
        table[source.event_id_column].cast("int64").name(EVENT_ID),
        table[source.start_date_column].cast("date").name(START_DATE),
        table[source.end_date_column].cast("date").name(END_DATE),
        ibis.literal(source.domain).name(DOMAIN),
        concept_expr.name(CONCEPT_ID),
        source_concept_expr.name(SOURCE_CONCEPT_ID),
        visit_occ_expr.name(VISIT_OCCURRENCE_ID),
        ibis.literal(int(criterion_index), type="int64").name(CRITERION_INDEX),
        ibis.literal(criterion_type).name(CRITERION_TYPE),
        ibis.literal(source.table_name).name(SOURCE_TABLE),
    )
    return standardized
