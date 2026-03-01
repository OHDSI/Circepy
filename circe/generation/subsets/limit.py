from __future__ import annotations

import ibis

from ..tables import COHORT_RESULT_SCHEMA
from .definitions import LimitSubsetOperator


def _first_last_per_subject(relation, *, first_only: bool):
    order = [
        relation.cohort_start_date.asc() if first_only else relation.cohort_start_date.desc(),
        relation.cohort_end_date.asc() if first_only else relation.cohort_end_date.desc(),
    ]
    window = ibis.window(group_by=[relation.subject_id], order_by=order)
    ranked = relation.mutate(_rank=ibis.row_number().over(window) + 1)
    return ranked.filter(ranked._rank == 1).drop("_rank")


def apply_limit_operator(
    relation,
    *,
    observation_period,
    operator: LimitSubsetOperator,
):
    if operator.first_only and operator.last_only:
        raise ValueError("LimitSubsetOperator cannot set both first_only and last_only.")

    relation_columns = list(COHORT_RESULT_SCHEMA.keys())
    current = relation.mutate(
        cohort_start_date=relation.cohort_start_date.cast("date"),
        cohort_end_date=relation.cohort_end_date.cast("date"),
    )

    if operator.calendar_start_date is not None:
        current = current.filter(
            current.cohort_start_date >= ibis.literal(operator.calendar_start_date).cast("date")
        )

    if operator.calendar_end_date is not None:
        current = current.filter(
            current.cohort_start_date <= ibis.literal(operator.calendar_end_date).cast("date")
        )

    if operator.min_cohort_duration_days is not None:
        current = current.filter(
            current.cohort_end_date
            >= (
                current.cohort_start_date
                + ibis.interval(days=int(operator.min_cohort_duration_days))
            )
        )

    if operator.min_prior_observation_days is not None:
        normalized_observation = observation_period.mutate(
            observation_period_start_date=observation_period.observation_period_start_date.cast(
                "date"
            ),
            observation_period_end_date=observation_period.observation_period_end_date.cast(
                "date"
            ),
        )
        joined = current.join(
            normalized_observation,
            predicates=[current.subject_id == normalized_observation.person_id],
            how="inner",
        )
        constrained = joined.filter(
            current.cohort_start_date
            >= normalized_observation.observation_period_start_date
        ).filter(
            current.cohort_start_date
            <= normalized_observation.observation_period_end_date
        ).filter(
            current.cohort_start_date
            >= (
                normalized_observation.observation_period_start_date
                + ibis.interval(days=int(operator.min_prior_observation_days))
            )
        )
        current = constrained.select(
            *[current[column] for column in relation_columns]
        ).distinct()

    if operator.first_only:
        current = _first_last_per_subject(current, first_only=True)
    elif operator.last_only:
        current = _first_last_per_subject(current, first_only=False)

    return current
