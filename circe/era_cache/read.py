"""Read features out of the era cache.

The read layer is where time-at-risk windows, aggregations and derived value
predicates live.  It never writes to the CDM and never regenerates eras unless
:func:`circe.era_cache.build.build_era_cache` is called explicitly.

Two read shapes are supported:

``feature_membership``
    ``(row_id, feature_key)`` for features matching inside a cohort era.  This is
    the workhorse for prevalence.

``feature_values``
    ``(row_id, feature_key, aggregation, value)`` for value-aware reads
    (``count``, ``num_events``, ``max_value`` and derived predicates).
"""

from __future__ import annotations

from dataclasses import dataclass

import ibis

from ..execution.typing import IbisBackendLike, Table
from .cohort_eras import CohortEraSpec, build_cohort_eras
from .schema import CATEGORICAL_TABLE, CONTINUOUS_TABLE, PRESENCE_TABLE

__all__ = [
    "SORT_MERGE_PREFIX",
    "EraRead",
    "FeatureWindow",
    "feature_membership",
    "load_cohort",
    "feature_values",
    "prevalence",
]

from .cohort_eras import CohortEraSpec as FeatureWindow  # re-exported alias

# Spark broadcast-joins any relation it thinks is small.  Feature-era tables grow
# to millions of rows and do not carry statistics, so Spark's default estimate
# makes it try to broadcast them and exhaust driver memory.  Prefixing read
# statements with this session setting forces a sort-merge join instead.
SORT_MERGE_PREFIX = "SET spark.sql.autoBroadcastJoinThreshold=-1;\n"


@dataclass(frozen=True)
class EraRead:
    """A read of the cache against one cohort and one window."""

    cohort: Table
    window: CohortEraSpec
    observation_period: Table | None = None


def load_cohort(
    table: Table,
    *,
    cohort_id: int | None = None,
    row_id_column: str | None = None,
) -> Table:
    """Return a cohort relation in the shape the read layer expects.

    The result exposes ``row_id``, ``subject_id``, ``cohort_start_date`` and
    ``cohort_end_date``.  ``row_id`` defaults to ``subject_id``; pass
    ``row_id_column`` for cohorts with several entries per subject.
    """
    if cohort_id is not None:
        table = table.filter(table.cohort_definition_id.cast("int64") == int(cohort_id))
    row_id = (
        table[row_id_column].cast("int64") if row_id_column is not None else table.subject_id.cast("int64")
    )
    return table.select(
        row_id.name("row_id"),
        table.subject_id.cast("int64").name("subject_id"),
        table.cohort_start_date.cast("date").name("cohort_start_date"),
        table.cohort_end_date.cast("date").name("cohort_end_date"),
    ).distinct()


def _read(backend: IbisBackendLike, table_name: str, schema: str | None) -> Table:
    if schema is not None:
        try:
            return backend.table(table_name, database=schema)
        except TypeError:
            pass
    return backend.table(table_name)


def _membership_relation(
    feature_eras: Table,
    cohort_eras: Table,
) -> Table:
    joined = feature_eras.join(cohort_eras, feature_eras.subject_id == cohort_eras.subject_id)
    matched = joined.filter(
        (feature_eras.era_start <= cohort_eras.end_day) & (feature_eras.era_end >= cohort_eras.start_day)
    )
    return matched.select(
        matched.row_id.cast("int64").name("row_id"),
        matched.feature_key,
    ).distinct()


def feature_membership(
    cohort: Table,
    *,
    windows: list[CohortEraSpec],
    backend: IbisBackendLike,
    cache_schema: str,
    observation_period: Table | None = None,
    feature_keys: list[str] | None = None,
) -> Table:
    """Return ``(row_id, window_index, feature_key)`` for matching features.

    ``window_index`` identifies which :class:`CohortEraSpec` matched so callers
    can compute several time-at-risk settings in one pass.
    """
    cohort_eras = build_cohort_eras(
        cohort,
        eras=windows,
        observation_period=observation_period,
    )

    # Presence, categorical and continuous features are stored separately; a
    # membership read spans all three so every cached feature class is visible.
    joined: Table | None = None
    for table_name in (PRESENCE_TABLE, CATEGORICAL_TABLE, CONTINUOUS_TABLE):
        eras = _read(backend, table_name, cache_schema).select(
            "feature_key", "subject_id", "era_start", "era_end"
        )
        if feature_keys:
            eras = eras.filter(eras.feature_key.isin(list(feature_keys)))
        part = eras.join(cohort_eras, eras.subject_id == cohort_eras.subject_id)
        part = part.filter(
            (eras.era_start <= cohort_eras.end_day) & (eras.era_end >= cohort_eras.start_day)
        ).select(
            part.row_id.cast("int64").name("row_id"),
            part.era_sequence.cast("int32").name("window_index"),
            part.feature_key,
        )
        joined = part if joined is None else joined.union(part, distinct=False)
    return joined.distinct()


def feature_values(
    cohort: Table,
    *,
    window: CohortEraSpec,
    backend: IbisBackendLike,
    cache_schema: str,
    observation_period: Table | None = None,
    predicate: str | None = None,
) -> Table:
    """Return value summaries for continuous features inside one window.

    ``predicate`` may be ``None`` (all events) or ``"above_normal"`` /
    ``"below_normal"`` / ``"within_normal"`` to filter on the cached reference
    range before summarising.
    """
    cohort_eras = build_cohort_eras(
        cohort,
        eras=[window],
        observation_period=observation_period,
    )
    feature_eras = _read(backend, CONTINUOUS_TABLE, cache_schema)
    if predicate is not None:
        feature_eras = _apply_normal_range(feature_eras, predicate)

    joined = feature_eras.join(cohort_eras, feature_eras.subject_id == cohort_eras.subject_id)
    matched = joined.filter(
        (feature_eras.era_start <= cohort_eras.end_day) & (feature_eras.era_end >= cohort_eras.start_day)
    )
    aggregated = matched.group_by(matched.row_id, matched.feature_key).aggregate(
        num_events=matched.count().cast("int64"),
        max_value=matched.value_num.max(),
        mean_value=matched.value_num.mean(),
        min_value=matched.value_num.min(),
    )
    # ``last_value`` is the value of the most recent event, not the maximum.
    ranked = matched.mutate(
        _rn=ibis.row_number().over(
            ibis.window(
                group_by=[matched.row_id, matched.feature_key],
                order_by=[ibis.desc(matched.era_start), ibis.desc(matched.concept_id)],
            )
        )
    )
    latest = ranked.filter(ranked._rn == 0).select(
        ranked.row_id,
        ranked.feature_key,
        ranked.value_num.name("last_value"),
    )
    return aggregated.join(
        latest,
        [aggregated.row_id == latest.row_id, aggregated.feature_key == latest.feature_key],
    )


def _apply_normal_range(eras: Table, predicate: str) -> Table:
    value = eras.value_num
    if predicate == "above_normal":
        return eras.filter(value.notnull() & eras.range_high.notnull() & (value > eras.range_high))
    if predicate == "below_normal":
        return eras.filter(value.notnull() & eras.range_low.notnull() & (value < eras.range_low))
    if predicate == "within_normal":
        return eras.filter(
            value.notnull()
            & eras.range_low.notnull()
            & eras.range_high.notnull()
            & (value >= eras.range_low)
            & (value <= eras.range_high)
        )
    raise ValueError(f"Unknown normal-range predicate {predicate!r}.")


def prevalence(
    cohort: Table,
    *,
    windows: list[CohortEraSpec],
    backend: IbisBackendLike,
    cache_schema: str,
    observation_period: Table | None = None,
    feature_keys: list[str] | None = None,
) -> Table:
    """Return ``(window_index, feature_key, numerator, denominator, prevalence)``."""
    cohort_eras = build_cohort_eras(
        cohort,
        eras=windows,
        observation_period=observation_period,
    )
    membership = feature_membership(
        cohort,
        windows=windows,
        backend=backend,
        cache_schema=cache_schema,
        observation_period=observation_period,
    )
    denominators = cohort_eras.group_by(cohort_eras.era_sequence).aggregate(
        denominator=cohort_eras.row_id.nunique()
    )
    numerators = membership.group_by(membership.window_index, membership.feature_key).aggregate(
        numerator=membership.row_id.nunique()
    )

    # Report explicit zeros: a feature with no matches in a window must still
    # appear, otherwise callers conflate "absent" with "not requested".
    cache = _read(backend, PRESENCE_TABLE, cache_schema)
    available = cache.select(cache.feature_key).distinct()
    if feature_keys:
        available = available.filter(available.feature_key.isin(list(feature_keys)))

    grid = (
        denominators.select(denominators.era_sequence.name("window_index"))
        .cross_join(available)
        .select("window_index", "feature_key")
    )
    merged = grid.left_join(
        numerators,
        [grid.window_index == numerators.window_index, grid.feature_key == numerators.feature_key],
    )
    merged = merged.join(denominators, merged.window_index == denominators.era_sequence)
    numerator = ibis.coalesce(merged.numerator, 0).cast("int64")
    return merged.select(
        merged.window_index,
        merged.feature_key,
        numerator.name("numerator"),
        merged.denominator,
        (numerator.cast("float64") / merged.denominator.cast("float64")).name("prevalence"),
    )


def _apply_normal_range(eras: Table, predicate: str) -> Table:
    value = eras.value_num
    if predicate == "above_normal":
        return eras.filter(value.notnull() & eras.range_high.notnull() & (value > eras.range_high))
    if predicate == "below_normal":
        return eras.filter(value.notnull() & eras.range_low.notnull() & (value < eras.range_low))
    if predicate == "within_normal":
        return eras.filter(
            value.notnull()
            & eras.range_low.notnull()
            & eras.range_high.notnull()
            & (value >= eras.range_low)
            & (value <= eras.range_high)
        )
    raise ValueError(f"Unknown normal-range predicate {predicate!r}.")
