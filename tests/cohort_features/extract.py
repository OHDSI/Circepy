"""Basic cohort-first feature extraction.

The extractor turns a :class:`~circe.cohort_features.model.FeatureSet` into a
cohort definition set, generates the feature cohorts through the decomposable
cohort engine, and assembles a sparse ``(row_id, feature_id, value)`` matrix for
a target cohort.

This is deliberately a *basic* extractor:

* ``exists`` and ``count`` aggregations;
* optional window relative to the target index date;
* optional dense output with explicit zeros;
* database-native execution (the returned relations are lazy ibis expressions).

More advanced extraction (value features, temporal grids, embeddings) belongs in
the `circe.features` layer; this package is the cohort/feature bridge.
"""

from __future__ import annotations

from dataclasses import dataclass

import ibis

from ..cohort_definition_set._generate import generate_cohort_set
from ..execution.ibis.operations import create_table, read_table
from ..execution.ibis_compat import literal_rows_relation
from ..execution.typing import IbisBackendLike, Table
from .model import Feature, FeatureSet, FeatureWindow

__all__ = [
    "FeatureMatrix",
    "extract_feature_matrix",
    "write_feature_matrix",
]


@dataclass
class FeatureMatrix:
    """A lazy feature matrix and its metadata."""

    values: Table
    feature_ref: Table
    target: Table
    feature_cohort_table: str
    target_cohort_table: str

    def write(
        self,
        backend: IbisBackendLike,
        *,
        table_name: str = "feature_matrix",
        ref_table_name: str = "feature_ref",
        schema: str | None = None,
        overwrite: bool = True,
    ) -> dict[str, str]:
        create_table(
            backend,
            table_name=table_name,
            schema=schema,
            obj=self.values,
            overwrite=overwrite,
        )
        create_table(
            backend,
            table_name=ref_table_name,
            schema=schema,
            obj=self.feature_ref,
            overwrite=overwrite,
        )
        return {"values": table_name, "feature_ref": ref_table_name}


def _read(backend: IbisBackendLike, table_name: str, schema: str | None) -> Table:
    if schema is not None:
        try:
            return read_table(backend, table_name=table_name, schema=schema)
        except TypeError:
            pass
    return read_table(backend, table_name=table_name, schema=None)


def _feature_ref(features: list[Feature]) -> Table:
    rows = []
    for feature in features:
        window: FeatureWindow | None = feature.window
        rows.append(
            {
                "feature_id": int(feature.feature_id),
                "name": feature.name,
                "aggregation": feature.aggregation,
                "window_start": window.start_days if window is not None else None,
                "window_end": window.end_days if window is not None else None,
                "window_basis": window.basis if window is not None else None,
                "window_overlap": int(window.overlap) if window is not None else None,
                "tags": ",".join(feature.tags),
            }
        )
    schema = {
        "feature_id": "int64",
        "name": "string",
        "aggregation": "string",
        "window_start": "int64",
        "window_end": "int64",
        "window_basis": "string",
        "window_overlap": "int64",
        "tags": "string",
    }
    return literal_rows_relation(rows, schema=schema)


def _empty_values() -> Table:
    return literal_rows_relation(
        [],
        schema={"row_id": "int64", "feature_id": "int64", "value": "float64"},
    )


def _feature_values(
    feature: Feature,
    *,
    target: Table,
    feature_cohorts: Table,
) -> Table:
    feature_rows = (
        feature_cohorts.filter(feature_cohorts.cohort_definition_id == int(feature.feature_id))
        .select(
            feature_cohorts.subject_id.cast("int64").name("subject_id"),
            feature_cohorts.cohort_start_date.cast("date").name("feature_start"),
            feature_cohorts.cohort_end_date.cast("date").name("feature_end"),
        )
        .distinct()
    )

    joined = target.join(feature_rows, target.subject_id == feature_rows.subject_id)
    window = feature.window
    if window is not None:
        upper = target.index_date + ibis.interval(days=int(window.end_days))
        lower = (
            target.index_date + ibis.interval(days=int(window.start_days))
            if window.start_days is not None
            else None
        )
        if window.overlap:
            predicate = joined.feature_start <= upper
            if lower is not None:
                predicate = predicate & (joined.feature_end >= lower)
        else:
            date = joined.feature_start if window.basis == "start" else joined.feature_end
            predicate = date <= upper
            if lower is not None:
                predicate = predicate & (date >= lower)
        joined = joined.filter(predicate)

    if feature.aggregation == "exists":
        return (
            joined.select(joined.row_id.cast("int64"))
            .distinct()
            .mutate(
                feature_id=ibis.literal(int(feature.feature_id), type="int64"),
                value=ibis.literal(1.0, type="float64"),
            )
            .select("row_id", "feature_id", "value")
        )

    if feature.aggregation == "count":
        return (
            joined.group_by(joined.row_id)
            .aggregate(value=joined.count().cast("float64"))
            .mutate(feature_id=ibis.literal(int(feature.feature_id), type="int64"))
            .select("row_id", "feature_id", "value")
        )

    raise ValueError(f"Unsupported aggregation {feature.aggregation!r}.")


def _union_values(parts: list[Table]) -> Table:
    if not parts:
        return _empty_values()
    result = parts[0]
    for part in parts[1:]:
        result = result.union(part, distinct=False)
    return result


def extract_feature_matrix(
    features: FeatureSet | list[Feature],
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    target_cohort_table: str,
    target_cohort_id: int | None = None,
    target_schema: str | None = None,
    feature_cohort_table: str = "feature_cohort",
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    shared: bool = True,
    include_zeros: bool = True,
    row_id_column: str | None = None,
) -> FeatureMatrix:
    """Generate feature cohorts and assemble a feature matrix.

    Args:
        features: Feature set (or list of features).
        backend: Ibis backend.
        cdm_schema: OMOP CDM schema.
        target_cohort_table: Cohort table defining the target population.
        target_cohort_id: Target cohort id; ``None`` uses all rows.
        target_schema: Schema for the target cohort table (defaults to
            ``results_schema``).
        feature_cohort_table: Table that feature cohorts are written to.
        results_schema: Schema for generated feature cohorts and outputs.
        vocabulary_schema: Vocabulary schema (defaults to ``cdm_schema``).
        shared: Use the decomposable shared-checkpoint executor.
        include_zeros: Emit explicit zero rows for every target/feature pair.
        row_id_column: Optional target-table column to use as ``row_id``.
            Defaults to ``subject_id`` (one target entry per subject).
    """
    feature_list = list(features.features if isinstance(features, FeatureSet) else features)
    if not feature_list:
        raise ValueError("extract_feature_matrix requires at least one feature.")

    feature_set = features if isinstance(features, FeatureSet) else FeatureSet(features=feature_list)
    cohort_set = feature_set.to_cohort_definition_set()

    generate_cohort_set(
        cohort_set,
        backend=backend,
        cdm_schema=cdm_schema,
        cohort_table=feature_cohort_table,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema or cdm_schema,
        shared=shared,
    )

    feature_cohorts = _read(backend, feature_cohort_table, results_schema)
    target_table = _read(backend, target_cohort_table, target_schema or results_schema)

    target = target_table
    if target_cohort_id is not None:
        target = target.filter(target.cohort_definition_id.cast("int64") == int(target_cohort_id))
    row_id_expr = (
        target[row_id_column].cast("int64") if row_id_column is not None else target.subject_id.cast("int64")
    )
    target = target.select(
        row_id_expr.name("row_id"),
        target.subject_id.cast("int64").name("subject_id"),
        target.cohort_definition_id.cast("int64").name("cohort_definition_id"),
        target.cohort_start_date.cast("date").name("index_date"),
        target.cohort_end_date.cast("date").name("cohort_end_date"),
    ).distinct()

    parts = [
        _feature_values(feature, target=target, feature_cohorts=feature_cohorts) for feature in feature_list
    ]
    values = _union_values(parts)

    feature_ref = _feature_ref(feature_list)
    if include_zeros:
        grid = target.select(target.row_id).distinct().cross_join(feature_ref.select("feature_id"))
        values = grid.left_join(
            values,
            [
                grid.row_id == values.row_id,
                grid.feature_id == values.feature_id,
            ],
        ).select(
            grid.row_id,
            grid.feature_id,
            ibis.coalesce(values.value, 0.0).cast("float64").name("value"),
        )
    return FeatureMatrix(
        values=values,
        feature_ref=feature_ref,
        target=target,
        feature_cohort_table=feature_cohort_table,
        target_cohort_table=target_cohort_table,
    )


def write_feature_matrix(
    matrix: FeatureMatrix,
    *,
    backend: IbisBackendLike,
    table_name: str = "feature_matrix",
    ref_table_name: str = "feature_ref",
    schema: str | None = None,
) -> dict[str, str]:
    """Materialise a feature matrix and its reference table."""
    return matrix.write(
        backend,
        table_name=table_name,
        ref_table_name=ref_table_name,
        schema=schema,
    )
