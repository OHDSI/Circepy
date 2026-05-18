from __future__ import annotations

import contextlib
import hashlib
import json
import logging
from collections.abc import Callable, Mapping
from typing import Any

import ibis

from ..errors import CompilationError
from ..normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem
from ..plan.schema import CONCEPT_ID
from ..typing import IbisBackendLike, Table
from .operations import create_table as _create_table_impl
from .operations import insert_relation, table_exists

logger = logging.getLogger(__name__)

_CODESET_TABLE = "__cg_codesets"
_CACHE_TABLE_NAME = "_circe_codeset_cache"


def _codeset_cache_table(cohort_table: str) -> str:
    """Return the codeset cache table name derived from the cohort table name.

    Two cohort tables in the same schema get separate caches, avoiding
    collisions when multiple CDMs share a results schema.
    """
    return f"_{cohort_table}_codeset_cache"


def _staging_table(cohort_table: str, cohort_id: int, stage: str) -> str:
    """Return a staging table name derived from the cohort table and id."""
    return f"__{cohort_table}_{cohort_id}_{stage}"


def ensure_codeset_cache(
    backend: IbisBackendLike, *, cohort_table: str, results_schema: str | None = None
) -> None:
    """Create the codeset cache table with an empty schema if it doesn't exist.

    Matches the pattern used by ``upsert_generation_history`` in the checksum
    store: create with a simple ibis memtable, then insert data separately.
    """
    from ..ibis.operations import table_exists

    cache_name = _codeset_cache_table(cohort_table)
    if table_exists(backend, table_name=cache_name, schema=results_schema):
        return

    empty = ibis.memtable(
        {"cache_key": [], CONCEPT_ID: []},
        schema={"cache_key": "string", CONCEPT_ID: "int64"},
    )
    _create_table_impl(
        backend,
        table_name=cache_name,
        schema=results_schema,
        obj=empty,
        overwrite=False,
    )


def _compute_cache_key(items: tuple[NormalizedConceptSetItem, ...]) -> str:
    """Deterministic SHA-256 hash of sorted concept set items."""
    canonical = sorted(
        (item.concept_id, item.is_excluded, item.include_descendants, item.include_mapped) for item in items
    )
    payload = json.dumps(canonical, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _vocabulary_table(
    table_name: str,
    *,
    vocabulary_schema: str | None,
    table_getter: Callable[[str, str | None], Table],
) -> Table:
    try:
        return table_getter(table_name, vocabulary_schema)
    except Exception as exc:
        raise CompilationError(
            f"Ibis executor compilation error: failed to access vocabulary table '{table_name}'."
        ) from exc


def _descendant_expression(
    ancestor_ids: tuple[int, ...],
    *,
    table_getter: Callable[[str, str | None], Table],
    vocabulary_schema: str | None,
) -> Table:
    """Build lazy ibis expression for descendant concept IDs of given ancestors.

    SELECT descendant_concept_id
    FROM concept c
    JOIN concept_ancestor ca ON c.concept_id = ca.descendant_concept_id
    WHERE ca.ancestor_concept_id IN (...) AND c.invalid_reason IS NULL
    """
    concept = _vocabulary_table("concept", vocabulary_schema=vocabulary_schema, table_getter=table_getter)
    concept_ancestor = _vocabulary_table(
        "concept_ancestor", vocabulary_schema=vocabulary_schema, table_getter=table_getter
    )
    return (
        concept_ancestor.join(concept, concept_ancestor.descendant_concept_id == concept.concept_id)
        .filter(concept_ancestor.ancestor_concept_id.isin(ancestor_ids))
        .filter(concept.invalid_reason.isnull())
        .select(concept_ancestor.descendant_concept_id.name(CONCEPT_ID))
        .distinct()
    )


def _mapped_expression(
    concept_ids: tuple[int, ...],
    *,
    table_getter: Callable[[str, str | None], Table],
    vocabulary_schema: str | None,
) -> Table:
    """Build lazy ibis expression for mapped-to concept IDs.

    SELECT DISTINCT cr.concept_id_1 AS concept_id
    FROM concept_relationship cr
    WHERE cr.concept_id_2 IN (...)
      AND cr.relationship_id = 'Maps to'
      AND cr.invalid_reason IS NULL
    """
    concept_relationship = _vocabulary_table(
        "concept_relationship", vocabulary_schema=vocabulary_schema, table_getter=table_getter
    )
    return (
        concept_relationship.filter(concept_relationship.concept_id_2.isin(concept_ids))
        .filter(concept_relationship.relationship_id == "Maps to")
        .filter(concept_relationship.invalid_reason.isnull())
        .select(concept_relationship.concept_id_1.name(CONCEPT_ID))
        .distinct()
    )


def build_concept_set_expression(
    concept_set: NormalizedConceptSet,
    *,
    table_getter: Callable[[str, str | None], Table],
    vocabulary_schema: str | None,
) -> Table:
    """Build a lazy ibis Table expression that resolves all concept IDs for one concept set.

    The returned ibis expression is never executed at build time -- it becomes
    a subquery embedded in the final cohort SQL.  The database engine performs
    the concept-ancestor and concept-relationship joins at execution time.
    """
    include_parts: list[Table] = []
    exclude_ids: list[int] = []

    for item in concept_set.items:
        if item.concept_id is None:
            continue

        direct: tuple[int, ...] = (int(item.concept_id),)

        if item.include_descendants:
            desc = _descendant_expression(
                direct, table_getter=table_getter, vocabulary_schema=vocabulary_schema
            )
        else:
            desc = ibis.memtable({"concept_id": [int(item.concept_id)]}, schema={"concept_id": "int64"})
            # For exclude items without descendants, just track the concept id
            if item.is_excluded:
                exclude_ids.append(int(item.concept_id))
                continue

        if item.include_mapped:
            mapped = _mapped_expression(
                direct, table_getter=table_getter, vocabulary_schema=vocabulary_schema
            )
            if item.include_descendants:
                # Need mapped for both direct AND descendants
                desc_mapped = _mapped_expression(
                    direct, table_getter=table_getter, vocabulary_schema=vocabulary_schema
                )
                full = _union_all_tables([desc, desc_mapped])
            else:
                full = _union_all_tables([desc, mapped])
        else:
            full = desc

        if item.is_excluded:
            if item.include_descendants or item.include_mapped:
                # Complex exclude with expansion needs anti-join
                include_parts.append(full)
                exclude_ids.append(None)  # marker for complex exclude
            else:
                exclude_ids.append(int(item.concept_id))
        else:
            include_parts.append(full)

    # Build include part
    if not include_parts:
        if not exclude_ids:
            return ibis.memtable({"concept_id": []}, schema={"concept_id": "int64"})
        # Only simple excludes -- just exclude those IDs from everything
        concept = _vocabulary_table("concept", vocabulary_schema=vocabulary_schema, table_getter=table_getter)
        return concept.filter(
            ~concept.concept_id.isin(ibis.literal(list(exclude_ids), type="array<int64>"))
        ).select(concept.concept_id.name(CONCEPT_ID))

    # Actually, let me reconsider the exclude handling. Simple excludes (plain IDs with no
    # descendants/mapped) can be handled via anti-join after the include union.
    # Complex excludes (with descendants/mapped) need to be treated as included items
    # that are then excluded via anti-join.
    # For simplicity and correctness, let me handle excludes uniformly via anti-join.

    return _build_codeset_expression(
        concept_set, table_getter=table_getter, vocabulary_schema=vocabulary_schema
    )


def _build_codeset_expression(
    concept_set: NormalizedConceptSet,
    *,
    table_getter: Callable[[str, str | None], Table],
    vocabulary_schema: str | None,
) -> Table:
    """Build lazy ibis expression for a concept set with include/exclude logic."""
    include_parts: list[Table] = []
    exclude_parts: list[Table] = []

    for item in concept_set.items:
        if item.concept_id is None:
            continue

        direct: tuple[int, ...] = (int(item.concept_id),)

        # Build base expression for this item
        if item.include_descendants:
            desc = _descendant_expression(
                direct, table_getter=table_getter, vocabulary_schema=vocabulary_schema
            )
            base = _union_all_tables(
                [
                    ibis.memtable({"concept_id": [int(item.concept_id)]}, schema={"concept_id": "int64"}),
                    desc,
                ]
            )
        else:
            base = ibis.memtable({"concept_id": [int(item.concept_id)]}, schema={"concept_id": "int64"})

        if item.include_mapped:
            mapped = _mapped_expression(
                direct, table_getter=table_getter, vocabulary_schema=vocabulary_schema
            )
            base = _union_all_tables([base, mapped])

        if item.is_excluded:
            exclude_parts.append(base)
        else:
            include_parts.append(base)

    if not include_parts:
        return ibis.memtable({"concept_id": []}, schema={"concept_id": "int64"})

    # Union all include parts
    if len(include_parts) == 1:
        result = include_parts[0]
    else:
        result = include_parts[0]
        for part in include_parts[1:]:
            result = result.union(part, distinct=False)

    result = result.distinct()

    # Anti-join excluded concepts
    for e in exclude_parts:
        marked = e.mutate(_cm=ibis.literal(1, type="int64"))
        result = result.join(marked, result.concept_id == marked.concept_id, how="left")
        result = result.filter(result._cm.isnull()).drop("_cm")

    return result.select(result.concept_id.name(CONCEPT_ID))


def _union_all_tables(tables: list[Table]) -> Table:
    """Union multiple single-column ibis tables using binary-tree merge.

    Binary-tree merge caps expression-tree depth at O(log n) instead of
    O(n), avoiding deeply nested UNION ALL chains for large numbers of
    tables (e.g. 100+ concept sets).
    """
    if not tables:
        raise ValueError("_union_all_tables requires at least one table")
    if len(tables) == 1:
        return tables[0]
    mid = len(tables) // 2
    left = _union_all_tables(tables[:mid])
    right = _union_all_tables(tables[mid:])
    return left.union(right, distinct=False)


def _drop_table(
    backend: IbisBackendLike,
    table_name: str,
    schema: str | None,
) -> None:
    """Safely drop a backend table."""
    with contextlib.suppress(Exception):
        backend.drop_table(table_name, database=schema, force=True)


def _table_getter_from_backend(
    backend: IbisBackendLike,
    schema: str,
) -> Callable[[str, str | None], Table]:
    """Build a table_getter callable from an ibis backend."""

    def _getter(table_name: str, table_schema: str | None) -> Table:
        try:
            if table_schema is not None:
                return backend.table(table_name, database=table_schema)
        except TypeError:
            pass
        return backend.table(table_name)

    return _getter


def build_batch_codeset_table(
    *,
    backend: IbisBackendLike,
    concept_sets: Mapping[int, NormalizedConceptSet],
    batch_table_name: str = _CODESET_TABLE,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    use_persistent_cache: bool = False,
    temporary: bool = False,
    cohort_table: str = "cohort",
) -> Table:
    """Populate a database table ``batch_table_name`` with all concept set IDs.

    The table has schema ``(codeset_id INT64, concept_id INT64)`` and is
    overwritten each call.  Each concept set in *concept_sets* is resolved
    via lazy ibis expressions that join concept_ancestor and
    concept_relationship -- the database engine performs the expansion.

    When *use_persistent_cache* is True, previously-resolved checksums are
    loaded from the codeset cache (named from *cohort_table*) so that
    already-expanded concept sets skip the vocabulary-table queries.
    """
    cache_table_name = _codeset_cache_table(cohort_table)
    table_getter = _table_getter_from_backend(backend, vocabulary_schema or "")

    # Collect cache keys and check persistent cache
    cache_hits: dict[int, list[int]] = {}
    uncached: list[tuple[int, NormalizedConceptSet]] = []
    if use_persistent_cache:
        for cid, cset in concept_sets.items():
            if not cset.items:
                continue
            key = _compute_cache_key(cset.items)
            cached = _read_codeset_cache(
                backend, cache_key=key, schema=results_schema, table_name=cache_table_name
            )
            if cached is not None:
                cache_hits[cid] = list(cached)
            else:
                uncached.append((cid, cset))
    else:
        uncached = list(concept_sets.items())

    # Build the full batch query
    parts: list[Table] = []

    # Cache hits: just use the cached IDs
    for cid, ids in cache_hits.items():
        if ids:
            tbl = ibis.memtable(
                {"codeset_id": [cid] * len(ids), "concept_id": ids},
                schema={"codeset_id": "int64", "concept_id": "int64"},
            )
            parts.append(tbl)

    # Split uncached into simple (direct IDs only) and complex (needs expansion)
    simple_rows: list[dict[str, Any]] = []
    complex_csets: list[tuple[int, NormalizedConceptSet]] = []
    for cid, cset in uncached:
        if not cset.items:
            continue
        if _needs_vocabulary_expansion({cid: cset}):
            complex_csets.append((cid, cset))
        else:
            for item in cset.items:
                if not item.is_excluded and item.concept_id is not None:
                    simple_rows.append({"codeset_id": int(cid), "concept_id": int(item.concept_id)})

    # Batch all simple IDs into one memtable
    if simple_rows:
        parts.append(
            ibis.memtable(
                simple_rows,
                schema={"codeset_id": "int64", "concept_id": "int64"},
            )
        )

    # Complex concept sets: build lazy expansion expressions
    for cid, cset in complex_csets:
        expr = _build_codeset_expression(cset, table_getter=table_getter, vocabulary_schema=vocabulary_schema)
        labeled = expr.mutate(codeset_id=ibis.literal(cid, type="int64")).select("codeset_id", CONCEPT_ID)
        parts.append(labeled)

    if not parts:
        # No concept sets at all -- create empty table
        empty = ibis.memtable(
            {"codeset_id": [], "concept_id": []},
            schema={"codeset_id": "int64", "concept_id": "int64"},
        )
        _create_table_impl(
            backend,
            table_name=batch_table_name,
            schema=results_schema,
            obj=empty,
            overwrite=True,
            temp=temporary,
        )
        return _read_table(backend, table_name=batch_table_name, schema=results_schema)

    # Union all parts and materialize
    combined = _union_all_tables(parts)

    _create_table_impl(
        backend,
        table_name=batch_table_name,
        schema=results_schema,
        obj=combined,
        overwrite=True,
        temp=temporary,
    )

    # Write newly-resolved concept sets to persistent cache
    if use_persistent_cache:
        for cid, cset in uncached:
            if not cset.items:
                continue
            key = _compute_cache_key(cset.items)
            if key in cache_hits:
                continue
            # Read back from the table to get resolved IDs for this codeset
            ref = _read_table(backend, table_name=batch_table_name, schema=results_schema)
            resolved = ref.filter(ref.codeset_id == cid).select(CONCEPT_ID).distinct().execute()
            cids = _extract_column(resolved, CONCEPT_ID)
            if cids:
                _write_codeset_cache(
                    backend,
                    cache_key=key,
                    concept_ids=cids,
                    schema=results_schema,
                    table_name=cache_table_name,
                )

    ref = _read_table(backend, table_name=batch_table_name, schema=results_schema)
    return ref


def _find_existing_checksums(
    backend: IbisBackendLike,
    checksums: set[str],
    schema: str | None,
    cache_table_name: str = _CACHE_TABLE_NAME,
) -> set[str]:
    """Return the subset of *checksums* that already exist in the cache table."""
    if not checksums:
        return set()

    if not table_exists(backend, table_name=cache_table_name, schema=schema):
        return set()
    tbl = _read_table(backend, table_name=cache_table_name, schema=schema)
    existing = tbl.filter(tbl.cache_key.isin(tuple(checksums))).select("cache_key").distinct().execute()
    if hasattr(existing, "columns"):
        return {str(v) for v in existing["cache_key"].tolist() if v is not None}
    return set()


def _populate_cache_batch(
    backend: IbisBackendLike,
    expression: Table,
    schema: str | None,
    cache_table_name: str = _CACHE_TABLE_NAME,
) -> None:
    """Insert a batch of concept set expansions into the codeset cache table.

    The table must already exist (created by :func:`ensure_codeset_cache`).
    When the backend does not support ``insert``, the table is recreated
    by UNION-ing existing cache data with the new expression.
    """
    try:
        insert_relation(
            expression,
            backend=backend,
            target_table=cache_table_name,
            target_schema=schema,
        )
    except Exception:
        logger.info(
            "Backend does not support insert for %s — recreating table via UNION",
            cache_table_name,
        )
        existing = _read_table(backend, table_name=cache_table_name, schema=schema)
        merged = existing.union(expression, distinct=False)
        _create_table_impl(
            backend,
            table_name=cache_table_name,
            schema=schema,
            obj=merged,
            overwrite=True,
        )


def resolve_concept_sets(
    concept_sets: Mapping[int, NormalizedConceptSet],
    *,
    backend: IbisBackendLike,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    cohort_table: str = "cohort",
) -> set[str]:
    """Resolve concept sets into the persistent codeset cache table.

    The cache table name is derived from *cohort_table* via
    ``_codeset_cache_table()`` so that separate cohort tables in the same
    schema get separate caches.

    For each unique concept set (identified by SHA-256 checksum):
    - Cache hit: skipped (already in the cache)
    - Cache miss: resolved via a single bulk query (vocabulary-table joins
      for descendants/mapped codes) and inserted into the cache.

    Returns the set of checksums that were resolved (cache misses).

    This function is idempotent and safe to call at any time, independent
    of cohort generation.  It never uses Python memory for resolved IDs --
    the resolution query runs directly on the backend.
    """
    if not concept_sets:
        return set()
    cache_table_name = _codeset_cache_table(cohort_table)
    checksum_map = _compute_checksum_map(concept_sets)
    existing = _find_existing_checksums(backend, set(checksum_map.values()), results_schema, cache_table_name)
    table_getter = _table_getter_from_backend(backend, vocabulary_schema or "")

    miss_parts: list[Table] = []
    resolved_keys: set[str] = set()

    for cid, key in checksum_map.items():
        if key in existing:
            continue
        try:
            expr = _build_codeset_expression(
                concept_sets[int(cid)], table_getter=table_getter, vocabulary_schema=vocabulary_schema
            )
            labeled = expr.mutate(cache_key=ibis.literal(key, type="string")).select("cache_key", CONCEPT_ID)
            miss_parts.append(labeled)
            resolved_keys.add(key)
        except Exception as exc:
            logger.warning("Failed to build concept set resolution query for key %s: %s", key, exc)

    if not miss_parts:
        return set()

    combined = _union_all_tables(miss_parts)
    try:
        _populate_cache_batch(backend, combined, results_schema, cache_table_name)
    except Exception as exc:
        logger.warning("Failed to populate codeset cache: %s", exc)

    return resolved_keys


def _compute_checksum_map(
    concept_sets: Mapping[int, NormalizedConceptSet],
) -> dict[int, str]:
    """Return a dict mapping ``codeset_id -> cache_key`` for each concept set."""
    result: dict[int, str] = {}
    for cid, cset in concept_sets.items():
        if cset.items:
            result[int(cid)] = _compute_cache_key(cset.items)
    return result


def build_single_codeset_table(
    *,
    backend: IbisBackendLike,
    concept_sets: Mapping[int, NormalizedConceptSet],
    batch_table_name: str = _CODESET_TABLE,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    use_persistent_cache: bool = False,
    cohort_table: str = "cohort",
) -> Table:
    """Build a codeset table for a single cohort.

    When *use_persistent_cache* is True, concept sets are stored in a
    persistent cache table keyed by SHA-256 checksum.  The cache table
    name is derived from *cohort_table* via ``_codeset_cache_table()``.
    Cache misses are resolved and inserted.  The per-cohort table is
    then built by selecting from the cache.

    When *use_persistent_cache* is False and all concept sets are simple
    (no descendant or mapped expansion), builds a lightweight memtable
    directly without any vocabulary-table queries.
    """
    checksum_map = _compute_checksum_map(concept_sets)
    needs_vocab = _needs_vocabulary_expansion(concept_sets)

    # Fast path: all concept sets are simple, no persistent cache needed
    if not needs_vocab and not use_persistent_cache:
        rows: list[dict[str, Any]] = []
        for cid, cset in concept_sets.items():
            for item in cset.items:
                if not item.is_excluded and item.concept_id is not None:
                    rows.append({"codeset_id": int(cid), "concept_id": int(item.concept_id)})
        if rows:
            data = ibis.memtable(rows, schema={"codeset_id": "int64", "concept_id": "int64"})
        else:
            data = ibis.memtable(
                {"codeset_id": [], "concept_id": []},
                schema={"codeset_id": "int64", "concept_id": "int64"},
            )
        _create_table_impl(
            backend,
            table_name=batch_table_name,
            schema=results_schema,
            obj=data,
            overwrite=True,
            temp=True,
        )
        return _read_table(backend, table_name=batch_table_name, schema=results_schema)

    if use_persistent_cache:
        # Resolve cache misses as a single bulk INSERT into the codeset cache.
        # Cache hits are skipped.  No per-concept-set round trips, no Python
        # memory for resolved IDs.
        resolve_concept_sets(
            concept_sets,
            backend=backend,
            results_schema=results_schema,
            vocabulary_schema=vocabulary_schema,
            cohort_table=cohort_table,
        )

        # Build per-cohort table from cache
        cache_name = _codeset_cache_table(cohort_table)
        cache_ref = _read_table(backend, table_name=cache_name, schema=results_schema)

        parts: list[Table] = []
        for cid, key in checksum_map.items():
            part = (
                cache_ref.filter(cache_ref.cache_key == key)
                .select(cache_ref.concept_id.name(CONCEPT_ID))
                .mutate(codeset_id=ibis.literal(int(cid), type="int64"))
                .select("codeset_id", CONCEPT_ID)
            )
            parts.append(part)

        combined = _union_all_tables(parts)
        _create_table_impl(
            backend,
            table_name=batch_table_name,
            schema=results_schema,
            obj=combined,
            overwrite=True,
        )
        return _read_table(backend, table_name=batch_table_name, schema=results_schema)

    # No cache, but some concept sets need vocabulary expansion
    table_getter = _table_getter_from_backend(backend, vocabulary_schema or "")

    parts = []
    for cid, cset in concept_sets.items():
        if not cset.items:
            continue
        needs_vocab = any(item.include_descendants or item.include_mapped for item in cset.items)
        if needs_vocab:
            expr = _build_codeset_expression(
                cset, table_getter=table_getter, vocabulary_schema=vocabulary_schema
            )
            labeled = expr.mutate(codeset_id=ibis.literal(int(cid), type="int64")).select(
                "codeset_id", CONCEPT_ID
            )
            parts.append(labeled)
        else:
            for item in cset.items:
                if not item.is_excluded and item.concept_id is not None:
                    rows = [{"codeset_id": int(cid), "concept_id": int(item.concept_id)}]
                    parts.append(ibis.memtable(rows, schema={"codeset_id": "int64", "concept_id": "int64"}))

    if not parts:
        empty = ibis.memtable(
            {"codeset_id": [], "concept_id": []},
            schema={"codeset_id": "int64", "concept_id": "int64"},
        )
        _create_table_impl(
            backend,
            table_name=batch_table_name,
            schema=results_schema,
            obj=empty,
            overwrite=True,
            temp=True,
        )
        return _read_table(backend, table_name=batch_table_name, schema=results_schema)

    combined = _union_all_tables(parts)
    _create_table_impl(
        backend,
        table_name=batch_table_name,
        schema=results_schema,
        obj=combined,
        overwrite=True,
        temp=True,
    )
    return _read_table(backend, table_name=batch_table_name, schema=results_schema)


def _needs_vocabulary_expansion(concept_sets: Mapping[int, NormalizedConceptSet]) -> bool:
    """Return True if any concept set requires vocabulary-table queries."""
    for cset in concept_sets.values():
        for item in cset.items:
            if item.include_descendants or item.include_mapped:
                return True
    return False


def _read_table(
    backend: IbisBackendLike,
    *,
    table_name: str,
    schema: str | None,
) -> Table:
    """Read a backend table as an ibis relation."""
    try:
        if schema is not None:
            return backend.table(table_name, database=schema)
    except TypeError:
        pass
    return backend.table(table_name)


def _extract_column(result: Any, col_name: str) -> tuple[int, ...]:
    """Extract a column from various ibis execute() return types."""
    if hasattr(result, "columns"):  # pandas
        values = result[col_name].tolist() if col_name in result.columns else result.iloc[:, 0].tolist()
    elif isinstance(result, (list, tuple, set)):
        values = list(result)
    else:
        values = [result] if result is not None else []
    return tuple(int(v) for v in values if v is not None)


def _read_codeset_cache(
    backend: IbisBackendLike,
    *,
    cache_key: str,
    schema: str | None,
    table_name: str,
) -> tuple[int, ...] | None:
    """Read cached concept IDs for a cache key from the persistent cache table."""

    try:
        if not table_exists(backend, table_name=table_name, schema=schema):
            return None
        tbl = _read_table(backend, table_name=table_name, schema=schema)
        rows = tbl.filter(tbl.cache_key == cache_key).select("concept_id").execute()
        ids = _extract_column(rows, "concept_id")
        return ids if ids else None
    except Exception:
        return None


def _write_codeset_cache(
    backend: IbisBackendLike,
    *,
    cache_key: str,
    concept_ids: tuple[int, ...],
    schema: str | None,
    table_name: str,
) -> None:
    """Persist resolved concept IDs to the cache table."""
    from .operations import insert_relation

    if not concept_ids:
        return

    try:
        data = ibis.memtable(
            {"cache_key": [cache_key] * len(concept_ids), "concept_id": list(concept_ids)},
            schema={"cache_key": "string", "concept_id": "int64"},
        )
        if not table_exists(backend, table_name=table_name, schema=schema):
            _create_table_impl(backend, table_name=table_name, schema=schema, obj=data)
            return
        insert_relation(data, backend=backend, target_table=table_name, target_schema=schema)
    except Exception:
        pass


def drop_codeset_table(
    backend: IbisBackendLike,
    *,
    batch_table_name: str = _CODESET_TABLE,
    results_schema: str | None = None,
) -> None:
    """Drop the batch codeset table."""
    _drop_table(backend, batch_table_name, results_schema)


def _filter_by_concept_table(
    table: Table,
    concept_table: Table,
    *,
    column: str,
    exclude: bool = False,
) -> Table:
    """Filter *table* by semi-join (include) or anti-join (exclude) against *concept_table*.

    Returns a new ibis relation with only the original *table* columns.
    """
    if not exclude:
        joined = table.join(concept_table, table[column] == concept_table.concept_id)
        return joined.select(*[joined[c] for c in table.columns])
    else:
        marked = concept_table.mutate(_cm=ibis.literal(1, type="int64"))
        joined = table.join(marked, table[column] == marked.concept_id, how="left")
        filtered = joined.filter(joined._cm.isnull())
        return filtered.select(*[filtered[c] for c in table.columns])
