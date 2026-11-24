"""Build the era cache.

A build is:

1. resolve every feature's concept set into one shared coding map;
2. generate missing features into a staging table, per feature family;
3. copy staged rows into the cache;
4. mark each feature complete in the registry.

Completed features are never regenerated.  A failed feature is marked incomplete
and does not block the rest of the build, which is what makes hour-long runs
resumable.

Every cache row is tagged with a ``cache_key`` derived from the CDM,
vocabulary and engine fingerprints.  Rebuilding after a CDM or vocabulary change
writes a new key rather than silently mixing generations.
"""

from __future__ import annotations

import contextlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import ibis

from ..execution.ibis.operations import (
    create_table,
    read_table,
    table_exists,
)
from ..execution.ibis_compat import literal_rows_relation
from ..execution.typing import IbisBackendLike, Table
from .extract import (
    build_coding_map,
    coding_map_table,
    feature_era_relation,
)
from .identity import cache_key
from .keys import ENGINE_FINGERPRINT, era_feature_key
from .schema import (
    CATEGORICAL_TABLE,
    CONTINUOUS_TABLE,
    PRESENCE_TABLE,
    REGISTRY_COLUMNS,
    REGISTRY_TABLE,
)
from .scope import CohortScope
from .specs import EraFeatureSpec

__all__ = ["BuildOutcome", "EraCache", "build_era_cache"]

logger = logging.getLogger(__name__)

_ERA_SCHEMA = {
    "presence": {
        "cache_key": "string",
        "feature_key": "string",
        "subject_id": "int64",
        "era_start": "date",
        "era_end": "date",
        "concept_id": "int64",
    },
    "categorical": {
        "cache_key": "string",
        "feature_key": "string",
        "subject_id": "int64",
        "era_start": "date",
        "era_end": "date",
        "concept_id": "int64",
        "value_concept_id": "int64",
        "unit_concept_id": "int64",
    },
    "continuous": {
        "cache_key": "string",
        "feature_key": "string",
        "subject_id": "int64",
        "era_start": "date",
        "era_end": "date",
        "concept_id": "int64",
        "value_num": "float64",
        "unit_concept_id": "int64",
        "range_low": "float64",
        "range_high": "float64",
        "operator_concept_id": "int64",
    },
}

_TABLE_FOR_CLASS = {
    "presence": PRESENCE_TABLE,
    "categorical": CATEGORICAL_TABLE,
    "continuous": CONTINUOUS_TABLE,
}


@dataclass
class BuildOutcome:
    """Summary of one build."""

    generated: list[str] = field(default_factory=list)
    reused: list[str] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    row_counts: dict[str, int] = field(default_factory=dict)
    elapsed_seconds: dict[str, float] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "generated": len(self.generated),
            "reused": len(self.reused),
            "failed": len(self.failed),
            "rows": int(sum(self.row_counts.values())),
        }


def run(backend: IbisBackendLike, relation: Table) -> Any:
    """Execute a relation through whichever interface the backend exposes."""
    execute = getattr(backend, "execute", None)
    if callable(execute):
        return execute(relation)
    return relation.execute()


def insert_relation(backend: IbisBackendLike, relation: Table, *, table_name: str, schema: str) -> None:
    """Append a relation using the backend's native insert path.

    The shared cohort helper routes through ibis' generic ``insert``, which on
    Spark falls back to CTAS.  Backends that expose their own ``insert`` (such
    as the Thrift adapter) get that instead.
    """
    native = getattr(backend, "insert", None)
    if callable(native):
        try:
            native(table_name, relation, database=schema)
            return
        except TypeError:
            native(table_name, relation)
            return
    from ..execution.ibis.operations import insert_relation as generic

    generic(relation, backend=backend, target_table=table_name, target_schema=schema)


def scalar_count(backend: IbisBackendLike, relation: Table) -> int:
    """Return the row count of a (possibly grouped) relation as an int."""
    result = run(backend, relation.count())
    if hasattr(result, "iloc"):
        return int(result.iloc[0, 0])
    if hasattr(result, "fetchall"):
        rows = result.fetchall()
        return int(rows[0][0]) if rows else 0
    if hasattr(result, "tolist"):
        values = result.tolist()
        return int(values[0]) if values else 0
    return int(result)


def _ensure_schema(backend: IbisBackendLike, schema: str) -> None:
    """Create the cache schema/database when the backend supports it."""
    existing = getattr(backend, "list_databases", None) or getattr(backend, "list_schemas", None)
    creator = getattr(backend, "create_database", None) or getattr(backend, "create_schema", None)
    if not callable(existing) or not callable(creator):
        return
    try:
        names = set(existing())
    except Exception:  # noqa: BLE001 - inspection is best effort
        return
    if schema in names:
        return
    try:
        creator(schema)
    except Exception:  # noqa: BLE001 - some backends create on demand
        return


def _ensure_table(
    backend: IbisBackendLike,
    *,
    table_name: str,
    schema: str,
    columns: dict[str, str],
) -> None:
    if table_exists(backend, table_name=table_name, schema=schema):
        return
    create_table(
        backend,
        table_name=table_name,
        schema=schema,
        obj=literal_rows_relation([], schema=columns),
        overwrite=False,
    )


def _registry_relation(rows: list[dict[str, Any]]) -> Table:
    return literal_rows_relation(rows, schema=REGISTRY_COLUMNS)


class EraCache:
    """Handle on an era cache stored in ``schema``."""

    def __init__(self, backend: IbisBackendLike, *, schema: str) -> None:
        self.backend = backend
        self.schema = schema
        self._ensure_layout()

    # -- layout ------------------------------------------------------------
    def _ensure_layout(self) -> None:
        _ensure_schema(self.backend, self.schema)
        _ensure_table(
            self.backend,
            table_name=PRESENCE_TABLE,
            schema=self.schema,
            columns=_ERA_SCHEMA["presence"],
        )
        _ensure_table(
            self.backend,
            table_name=CATEGORICAL_TABLE,
            schema=self.schema,
            columns=_ERA_SCHEMA["categorical"],
        )
        _ensure_table(
            self.backend,
            table_name=CONTINUOUS_TABLE,
            schema=self.schema,
            columns=_ERA_SCHEMA["continuous"],
        )
        _ensure_table(
            self.backend,
            table_name=REGISTRY_TABLE,
            schema=self.schema,
            columns=REGISTRY_COLUMNS,
        )

    def table(self, name: str) -> Table:
        return read_table(self.backend, table_name=name, schema=self.schema)

    # -- registry ----------------------------------------------------------
    def entries(self) -> dict[str, dict[str, Any]]:
        if not table_exists(self.backend, table_name=REGISTRY_TABLE, schema=self.schema):
            return {}
        relation = self.table(REGISTRY_TABLE)
        rows = run(
            self.backend,
            relation.select(
                "feature_key",
                "cache_key",
                "completed",
                "row_count",
            ),
        ).to_dict(orient="records")
        return {
            str(row["feature_key"]): {
                "cache_key": str(row["cache_key"]),
                "completed": bool(row["completed"]),
                "row_count": int(row["row_count"] or 0),
            }
            for row in rows
        }

    def _upsert(
        self,
        *,
        cache_key_value: str,
        entries: list[tuple[EraFeatureSpec, str, str, int, int, bool]],
    ) -> None:
        """Write registry rows, replacing any existing row for each feature key."""
        if not entries:
            return
        feature_keys = [entry[1] for entry in entries]
        table = self.table(REGISTRY_TABLE)
        stale = table.filter(table.feature_key.isin(feature_keys))
        if scalar_count(self.backend, stale) > 0:
            self._delete_registry(feature_keys)
        now = datetime.now(timezone.utc)
        rows = [
            {
                "feature_key": feature_key,
                "cache_key": cache_key_value,
                "family": spec.source_table,
                "feature_class": spec.feature_class,
                "table_name": table_name,
                "completed": bool(completed),
                "row_count": int(row_count),
                "subject_count": int(subject_count),
                "cdm_fingerprint": "",
                "vocab_fingerprint": "",
                "engine_fingerprint": ENGINE_FINGERPRINT,
                "updated_at": now,
                "completed_at": now if completed else None,
            }
            for spec, feature_key, table_name, row_count, subject_count, completed in entries
        ]
        insert_relation(
            self.backend,
            _registry_relation(rows),
            table_name=REGISTRY_TABLE,
            schema=self.schema,
        )

    def _delete_registry(self, feature_keys: list[str]) -> None:
        raw = getattr(self.backend, "raw_sql", None)
        statement = (
            f"DELETE FROM {self.schema}.{REGISTRY_TABLE} WHERE feature_key IN ("
            + ",".join(f"'{key}'" for key in feature_keys)
            + ")"
        )
        if callable(raw):
            raw(statement)
            return
        # Fallback for backends without raw SQL: drop matching rows via
        # create-or-replace is not supported, so raise a clear error.
        raise RuntimeError(
            "Backend does not support DELETE for registry upserts; "
            "reuse an existing feature key or pass force=True."
        )

    # -- writes ------------------------------------------------------------
    def replace_feature(
        self,
        *,
        cache_key_value: str,
        feature_key: str,
        table_name: str,
        relation: Table,
    ) -> int:
        raw = getattr(self.backend, "raw_sql", None)
        if callable(raw):
            raw(
                f"DELETE FROM {self.schema}.{table_name} "
                f"WHERE feature_key = '{feature_key}' AND cache_key = '{cache_key_value}'"
            )
        insert_relation(
            relation,
            backend=self.backend,
            target_table=table_name,
            target_schema=self.schema,
        )
        table = self.table(table_name)
        filtered = table.filter((table.feature_key == feature_key) & (table.cache_key == cache_key_value))
        return scalar_count(self.backend, filtered)

    # -- inspection --------------------------------------------------------
    def explain(self) -> dict[str, Any]:
        entries = self.entries()
        return {
            "schema": self.schema,
            "features": len(entries),
            "completed": sum(1 for entry in entries.values() if entry["completed"]),
            "rows": int(sum(entry["row_count"] for entry in entries.values())),
        }

    def completed_features(self) -> set[str]:
        return {key for key, entry in self.entries().items() if entry["completed"]}


def build_era_cache(
    specs: list[EraFeatureSpec],
    *,
    backend: IbisBackendLike,
    cache_schema: str,
    cdm_schema: str,
    vocabulary_schema: str | None = None,
    cdm_fingerprint: str | None = None,
    vocab_fingerprint: str | None = None,
    force: bool = False,
    session_prefix: str | None = None,
    scope: CohortScope | None = None,
) -> BuildOutcome:
    """Build or extend the era cache for *specs*.

    Args:
        scope: Which subjects to cache. Defaults to a cohort scope and **must**
            be given as a :func:`~circe.era_cache.scope.cohort_scope` or
            :func:`~circe.era_cache.scope.scope_from_cohort_table`; pass
            :func:`~circe.era_cache.scope.whole_cdm` explicitly to cache the
            entire CDM. The whole-CDM pipeline is a separate, much larger
            product and is never the default.

    Raises:
        ValueError: If no scope is supplied. Caching every person in the CDM by
            accident is expensive and hard to undo, so it has to be asked for.
    """
    if not specs:
        raise ValueError("build_era_cache requires at least one spec.")
    if scope is None:
        raise ValueError(
            "build_era_cache requires an explicit scope. Pass "
            "cohort_scope(cohort_ids, cohort_table=...) to cache a study "
            "population, or whole_cdm() if you really want the entire CDM."
        )

    features = {era_feature_key(spec): spec for spec in specs}
    cache_key_value = cache_key(
        cdm_schema=cdm_schema,
        vocabulary_schema=vocabulary_schema or cdm_schema,
        cdm_fingerprint=cdm_fingerprint,
        vocab_fingerprint=vocab_fingerprint,
        scope_fingerprint=scope.fingerprint(),
    )

    cache = EraCache(backend, schema=cache_schema)
    existing = cache.entries()

    pending: list[tuple[str, EraFeatureSpec]] = []
    outcome = BuildOutcome()
    for feature_key, spec in features.items():
        entry = existing.get(feature_key)
        if not force and entry is not None and entry["completed"] and entry["cache_key"] == cache_key_value:
            outcome.reused.append(feature_key)
            outcome.row_counts[feature_key] = entry["row_count"]
            continue
        pending.append((feature_key, spec))

    if not pending:
        return outcome

    prefix = session_prefix or f"__era_{uuid.uuid4().hex[:8]}_"

    # Resolve the subject population once; every feature joins against it in the
    # database, so a cohort-scoped build never scans the whole CDM.
    subjects = None if scope.is_whole_cdm else scope.subjects(backend)

    coding_parts = {}
    for feature_key, spec in pending:
        coding_parts[feature_key] = build_coding_map(
            spec,
            backend=backend,
            vocabulary_schema=vocabulary_schema or cdm_schema,
        )
    coding = coding_map_table(
        coding_parts,
        backend=backend,
        table_name="era_coding",
        schema=cache_schema,
        session_prefix=prefix,
    )

    try:
        # Group by family so staging tables are small and per-family failures
        # cost at most that family.
        families: dict[str, list[tuple[str, EraFeatureSpec]]] = {}
        for feature_key, spec in pending:
            families.setdefault(spec.feature_class, []).append((feature_key, spec))

        for feature_class, members in families.items():
            _build_family(
                members,
                feature_class=feature_class,
                cache=cache,
                cache_key_value=cache_key_value,
                backend=backend,
                cdm_schema=cdm_schema,
                coding=coding,
                prefix=prefix,
                subjects=subjects,
                outcome=outcome,
            )
    finally:
        with contextlib.suppress(Exception):
            backend.drop_table(f"{prefix}era_coding", database=cache_schema, force=True)

    return outcome


def _build_family(
    members: list[tuple[str, EraFeatureSpec]],
    *,
    feature_class: str,
    cache: EraCache,
    cache_key_value: str,
    backend: IbisBackendLike,
    cdm_schema: str,
    coding: Table,
    prefix: str,
    subjects: Table | None,
    outcome: BuildOutcome,
) -> None:
    table_name = _TABLE_FOR_CLASS[feature_class]
    staging_name = f"{prefix}stage_{feature_class}"
    parts: list[Table] = []
    registry_rows: list[tuple[EraFeatureSpec, str, str, int, int, bool]] = []

    for feature_key, spec in members:
        started = datetime.now(timezone.utc)
        try:
            era = feature_era_relation(
                spec,
                backend=backend,
                cdm_schema=cdm_schema,
                feature_key=feature_key,
                coding=coding,
                subjects=subjects,
            )
            projection = era.select(
                ibis.literal(cache_key_value).name("cache_key"),
                era.feature_key,
                era.subject_id,
                era.era_start,
                era.era_end,
                era.concept_id,
                *[
                    era[column]
                    for column in _ERA_SCHEMA[feature_class]
                    if column
                    not in {"cache_key", "feature_key", "subject_id", "era_start", "era_end", "concept_id"}
                ],
            )
            parts.append(projection)
            registry_rows.append((spec, feature_key, table_name, 0, 0, False))
        except Exception as exc:  # noqa: BLE001 - one feature must not stop the family
            outcome.failed.append({"feature_key": feature_key, "error": f"{type(exc).__name__}: {exc}"})
        finally:
            outcome.elapsed_seconds[feature_key] = (datetime.now(timezone.utc) - started).total_seconds()

    if not parts:
        return

    combined = parts[0]
    for part in parts[1:]:
        combined = combined.union(part, distinct=False)
    create_table(
        backend,
        table_name=staging_name,
        schema=cache.schema,
        obj=combined,
        overwrite=True,
    )

    staged = read_table(backend, table_name=staging_name, schema=cache.schema)
    grouped = run(
        backend,
        staged.group_by(staged.feature_key).aggregate(
            row_count=staged.count(),
            subject_count=staged.subject_id.nunique(),
        ),
    ).to_dict(orient="records")
    counts = {str(row["feature_key"]): int(row["row_count"]) for row in grouped}
    subjects = {str(row["feature_key"]): int(row["subject_count"]) for row in grouped}

    completed_rows: list[tuple[EraFeatureSpec, str, str, int, int, bool]] = []
    for spec, feature_key, table_name_, _row_count, _subject_count, _completed in registry_rows:
        rows = counts.get(feature_key, 0)
        if rows == 0:
            outcome.failed.append({"feature_key": feature_key, "error": "feature produced no rows"})
            cache._upsert(
                cache_key_value=cache_key_value,
                entries=[(spec, feature_key, table_name_, 0, 0, False)],
            )
            continue
        # Publish this feature's rows, keyed by feature and cache generation.
        feature_rows = staged.filter(staged.feature_key == feature_key)
        raw = getattr(backend, "raw_sql", None)
        if callable(raw):
            raw(
                f"DELETE FROM {cache.schema}.{table_name_} "
                f"WHERE feature_key = '{feature_key}' AND cache_key = '{cache_key_value}'"
            )
        insert_relation(
            backend,
            feature_rows,
            table_name=table_name_,
            schema=cache.schema,
        )
        completed_rows.append((spec, feature_key, table_name_, rows, subjects.get(feature_key, 0), True))
        outcome.generated.append(feature_key)
        outcome.row_counts[feature_key] = rows

    cache._upsert(cache_key_value=cache_key_value, entries=completed_rows)

    with contextlib.suppress(Exception):
        backend.drop_table(staging_name, database=cache.schema, force=True)
