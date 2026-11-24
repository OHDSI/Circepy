"""Extract feature eras from the CDM.

This module owns the only place that knows how to turn a CDM domain table plus
an :class:`~circe.era_cache.specs.EraFeatureSpec` into era rows.  It reuses the
cohort engine's concept-set resolution so descendants, mapped concepts and
exclusions behave identically to cohort definitions.

Nothing here knows about a cohort, an index date or a time-at-risk window. That
separation is what makes the cache reusable.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import ibis

from ..execution.ibis.codesets import _build_codeset_expression
from ..execution.ibis.operations import create_table, read_table
from ..execution.ibis_compat import literal_rows_relation
from ..execution.normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem
from ..execution.typing import IbisBackendLike, Table
from .keys import era_feature_key
from .specs import EraFeatureSpec

__all__ = [
    "DISCRETE_TABLES",
    "build_coding_map",
    "coding_map_table",
    "era_feature_keys",
    "feature_era_relation",
]

# Tables whose events are points in time rather than intervals.
DISCRETE_TABLES = {
    "measurement",
    "observation",
    "procedure_occurrence",
    "specimen",
    "death",
}

_VALUE_TABLES = {"measurement", "observation"}


def _normalized_set(spec: EraFeatureSpec) -> NormalizedConceptSet:
    if spec.concept_set is None:
        items = tuple(
            NormalizedConceptSetItem(
                concept_id=int(concept_id),
                is_excluded=False,
                include_descendants=bool(spec.include_descendants),
                include_mapped=False,
            )
            for concept_id in spec.concept_ids
        )
        return NormalizedConceptSet(set_id=1, items=items)

    expression = spec.concept_set
    items: list[NormalizedConceptSetItem] = []
    if expression.concept is not None and expression.concept.concept_id is not None:
        items.append(
            NormalizedConceptSetItem(
                concept_id=int(expression.concept.concept_id),
                is_excluded=bool(expression.is_excluded),
                include_descendants=bool(expression.include_descendants),
                include_mapped=bool(expression.include_mapped),
            )
        )
    for item in expression.items or []:
        if item is None or item.concept is None or item.concept.concept_id is None:
            continue
        items.append(
            NormalizedConceptSetItem(
                concept_id=int(item.concept.concept_id),
                is_excluded=bool(item.is_excluded),
                include_descendants=bool(item.include_descendants),
                include_mapped=bool(item.include_mapped),
            )
        )
    return NormalizedConceptSet(set_id=1, items=tuple(items))


def build_coding_map(
    spec: EraFeatureSpec,
    *,
    backend: IbisBackendLike,
    vocabulary_schema: str | None,
) -> Table:
    """Return a ``concept_id`` relation containing every concept the spec accepts."""
    normalized = _normalized_set(spec)
    needs_expression = any(
        item.include_descendants or item.include_mapped or item.is_excluded for item in normalized.items
    )

    if not needs_expression:
        included = sorted(
            {
                int(item.concept_id)
                for item in normalized.items
                if not item.is_excluded and item.concept_id is not None
            }
        )
        return literal_rows_relation(
            [{"concept_id": concept_id} for concept_id in included],
            schema={"concept_id": "int64"},
        )

    def get(name: str, schema: str | None) -> Table:
        target = schema or vocabulary_schema
        if target is not None:
            return backend.table(name, database=target)
        return backend.table(name)

    relation = _build_codeset_expression(
        normalized,
        table_getter=get,
        vocabulary_schema=vocabulary_schema,
    )
    return relation.select(relation.concept_id.cast("int64").name("concept_id")).distinct()


def coding_map_table(
    mappings: Mapping[str, Table],
    *,
    backend: IbisBackendLike,
    table_name: str,
    schema: str | None,
    session_prefix: str = "",
) -> Table:
    """Materialise ``(feature_key, concept_id)`` for every feature in one build."""
    if mappings:
        parts = []
        for feature_key, mapped in mappings.items():
            parts.append(
                mapped.select(
                    ibis.literal(feature_key).name("feature_key"),
                    mapped.concept_id.cast("int64").name("concept_id"),
                )
            )
        relation = parts[0]
        for part in parts[1:]:
            relation = relation.union(part, distinct=False)
        relation = relation.distinct()
    else:
        relation = literal_rows_relation([], schema={"feature_key": "string", "concept_id": "int64"})

    name = f"{session_prefix}{table_name}"
    create_table(backend, table_name=name, schema=schema, obj=relation, overwrite=True)
    return read_table(backend, table_name=name, schema=schema)


def _era_bounds(spec: EraFeatureSpec, source: Table) -> tuple[object, object]:
    start = source[spec.start_date_column].cast("date")
    end_column = spec.end_date_column
    if spec.source_table in DISCRETE_TABLES or end_column is None:
        return start, start
    if end_column not in source.columns:
        return start, start
    end = source[end_column].cast("date")
    # Domains with optional end dates fall back to the start date.
    return start, ibis.coalesce(end, start)


def _type_column(spec: EraFeatureSpec) -> str:
    return f"{spec.source_table.removesuffix('_occurrence')}_type_concept_id"


def feature_era_relation(
    spec: EraFeatureSpec,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    feature_key: str,
    coding: Table,
    subjects: Table | None = None,
) -> Table:
    """Return the era rows selected by *spec* for one feature key.

    ``subjects`` optionally restricts the result to a lazy relation of
    ``subject_id`` — this is how a cohort-scoped build avoids scanning the whole
    CDM.  The join happens in the database; nothing is materialised here.
    """
    source = backend.table(spec.source_table, database=cdm_schema)
    columns = set(source.columns)

    concept_column = spec.concept_column
    if concept_column not in columns:
        raise ValueError(f"Source table {spec.source_table!r} has no column {concept_column!r}.")

    accepted = coding.filter(coding.feature_key == feature_key).select(
        coding.concept_id.cast("int64").name("concept_id")
    )
    joined = source.join(accepted, source[concept_column] == accepted.concept_id)

    if subjects is not None:
        joined = joined.join(subjects, joined.person_id.cast("int64") == subjects.subject_id)

    type_column = _type_column(spec)
    if spec.type_concept_ids and type_column in columns:
        joined = joined.filter(joined[type_column].isin([int(item) for item in spec.type_concept_ids]))
    if spec.status_concept_ids and "condition_status_concept_id" in columns:
        joined = joined.filter(
            joined.condition_status_concept_id.isin([int(item) for item in spec.status_concept_ids])
        )

    era_start, era_end = _era_bounds(spec, joined)

    base_columns = {
        "feature_key": ibis.literal(feature_key),
        "subject_id": joined.person_id.cast("int64"),
        "era_start": era_start,
        "era_end": era_end,
        "concept_id": joined[concept_column].cast("int64"),
    }

    if spec.feature_class == "presence":
        relation = joined.select(**base_columns)
        return relation.distinct()

    if spec.source_table not in _VALUE_TABLES:
        raise ValueError(
            f"Feature {spec.name!r}: {spec.feature_class} features require a table with value columns."
        )

    if spec.value_concept_ids:
        joined = joined.filter(
            joined.value_as_concept_id.isin([int(item) for item in spec.value_concept_ids])
        )
    if spec.unit_concept_ids:
        joined = joined.filter(joined.unit_concept_id.isin([int(item) for item in spec.unit_concept_ids]))

    def optional(column: str, dtype: str):
        return joined[column].cast(dtype) if column in columns else ibis.null().cast(dtype)

    era_start, era_end = _era_bounds(spec, joined)
    relation = joined.select(
        feature_key=ibis.literal(feature_key),
        subject_id=joined.person_id.cast("int64"),
        era_start=era_start,
        era_end=era_end,
        concept_id=joined[concept_column].cast("int64"),
        value_concept_id=optional("value_as_concept_id", "int64"),
        value_num=optional("value_as_number", "float64"),
        unit_concept_id=optional("unit_concept_id", "int64"),
        range_low=optional("range_low", "float64"),
        range_high=optional("range_high", "float64"),
        operator_concept_id=optional("operator_concept_id", "int64"),
    )
    return relation.distinct()


def era_feature_keys(specs: Iterable[EraFeatureSpec]) -> list[tuple[EraFeatureSpec, str]]:
    """Pair each spec with its content key."""
    return [(spec, era_feature_key(spec)) for spec in specs]
