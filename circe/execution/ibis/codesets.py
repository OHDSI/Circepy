from __future__ import annotations

import contextlib
import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any

import ibis

from ..errors import CompilationError
from ..normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem
from ..plan.schema import CONCEPT_ID
from ..typing import IbisBackendLike, Table
from .operations import create_table as _create_table_impl

_CODESET_TABLE = "__cg_codesets"
_CACHE_TABLE_NAME = "_circe_codeset_cache"


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
) -> Table:
    """Populate a database table ``batch_table_name`` with all concept set IDs.

    The table has schema ``(codeset_id INT64, concept_id INT64)`` and is
    overwritten each call.  Each concept set in *concept_sets* is resolved
    via lazy ibis expressions that join concept_ancestor and
    concept_relationship -- the database engine performs the expansion.

    When *use_persistent_cache* is True, previously-resolved checksums are
    loaded from ``_circe_codeset_cache`` so that already-expanded concept
    sets skip the vocabulary-table queries.

    Returns an ibis Table reference to the batch table.
    """
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
                backend, cache_key=key, schema=results_schema, table_name=_CACHE_TABLE_NAME
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
                    table_name=_CACHE_TABLE_NAME,
                )

    ref = _read_table(backend, table_name=batch_table_name, schema=results_schema)
    return ref


def _needs_vocabulary_expansion(concept_sets: Mapping[int, NormalizedConceptSet]) -> bool:
    """Return True if any concept set requires vocabulary-table queries."""
    for cset in concept_sets.values():
        for item in cset.items:
            if item.include_descendants or item.include_mapped:
                return True
    return False


def build_single_codeset_table(
    *,
    backend: IbisBackendLike,
    concept_sets: Mapping[int, NormalizedConceptSet],
    batch_table_name: str = _CODESET_TABLE,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
) -> Table:
    """Build a codeset table for a single cohort.

    When all concept sets use only direct concept IDs (no descendant or
    mapped expansion needed), builds a simple memtable -- no vocabulary
    tables required.  Falls back to full expansion otherwise.
    """
    if not _needs_vocabulary_expansion(concept_sets):
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

    return build_batch_codeset_table(
        backend=backend,
        concept_sets=concept_sets,
        batch_table_name=batch_table_name,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        use_persistent_cache=False,
        temporary=True,
    )


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
    from .operations import table_exists

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
    from .operations import insert_relation, table_exists

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
