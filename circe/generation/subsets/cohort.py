from __future__ import annotations

import ibis

from .definitions import CohortSubsetOperator


def _anchor_date(relation, anchor: str):
    if anchor == "end":
        return relation.cohort_end_date
    return relation.cohort_start_date


def apply_cohort_subset_operator(
    relation,
    *,
    subset_relation,
    operator: CohortSubsetOperator,
):
    current = relation.mutate(
        _row_id=(
            ibis.row_number().over(
                ibis.window(
                    order_by=[
                        relation.subject_id.asc(),
                        relation.cohort_start_date.asc(),
                        relation.cohort_end_date.asc(),
                    ]
                )
            )
            + 1
        )
    )

    subset = subset_relation.select(
        subset_relation.subject_id.name("_subset_subject_id"),
        subset_relation.cohort_start_date.name("_subset_start"),
        subset_relation.cohort_end_date.name("_subset_end"),
    )

    joined = current.join(
        subset,
        predicates=[current.subject_id == subset._subset_subject_id],
        how="inner",
    )

    target_anchor = _anchor_date(current, operator.target_anchor)
    subset_anchor = (
        subset._subset_end if operator.subset_anchor == "end" else subset._subset_start
    )
    lower = target_anchor + ibis.interval(days=int(operator.window_start_offset))
    upper = target_anchor + ibis.interval(days=int(operator.window_end_offset))

    window_match = (subset_anchor >= lower) & (subset_anchor <= upper)
    overlap = (current.cohort_start_date <= subset._subset_end) & (
        current.cohort_end_date >= subset._subset_start
    )

    if operator.relationship == "require_overlap":
        match_predicate = window_match & overlap
    else:
        match_predicate = window_match

    matched_ids = joined.filter(match_predicate).select(current._row_id).distinct()

    if operator.relationship == "exclude":
        result = current.anti_join(
            matched_ids,
            predicates=[current._row_id == matched_ids._row_id],
        )
    else:
        result = current.semi_join(
            matched_ids,
            predicates=[current._row_id == matched_ids._row_id],
        )

    return result.drop("_row_id")
