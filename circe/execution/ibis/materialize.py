from __future__ import annotations

from ..typing import Table


def project_to_ohdsi_cohort_table(relation: Table, *, cohort_id: int | None) -> Table:
    """Project a generic cohort relation into OHDSI cohort-table shape."""
    import ibis

    cohort_id_expr = (
        ibis.literal(int(cohort_id), type="int64") if cohort_id is not None else ibis.null().cast("int64")
    )
    return relation.select(
        cohort_id_expr.name("cohort_definition_id"),
        relation.person_id.cast("int64").name("subject_id"),
        relation.start_date.cast("date").name("cohort_start_date"),
        relation.end_date.cast("date").name("cohort_end_date"),
    )
