from __future__ import annotations

import ibis

from ..plan.events import EventSource

STANDARD_EVENT_COLUMNS = (
    "person_id",
    "event_id",
    "start_date",
    "end_date",
    "domain",
    "concept_id",
    "source_concept_id",
    "visit_occurrence_id",
    "criterion_index",
    "criterion_type",
    "source_table",
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
        table[source.person_id_column].cast("int64").name("person_id"),
        table[source.event_id_column].cast("int64").name("event_id"),
        table[source.start_date_column].cast("date").name("start_date"),
        table[source.end_date_column].cast("date").name("end_date"),
        ibis.literal(source.domain).name("domain"),
        concept_expr.name("concept_id"),
        source_concept_expr.name("source_concept_id"),
        visit_occ_expr.name("visit_occurrence_id"),
        ibis.literal(int(criterion_index), type="int64").name("criterion_index"),
        ibis.literal(criterion_type).name("criterion_type"),
        ibis.literal(source.table_name).name("source_table"),
    )
    return standardized
