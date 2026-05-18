from __future__ import annotations

import contextlib
from collections.abc import Callable, Mapping
from typing import Any

import ibis

from ..errors import CompilationError
from ..normalize.cohort import NormalizedConceptSet
from ..plan.schema import CONCEPT_ID
from ..typing import IbisBackendLike, Table
from .operations import create_table as _create_table_impl


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


def _build_codeset_expression(
    concept_set: NormalizedConceptSet,
    *,
    table_getter: Callable[[str, str | None], Table],
    vocabulary_schema: str | None,
) -> Table:
    """Build a lazy ibis expression for a concept set with include/exclude logic.

    Handles descendants, mapped codes, and exclusions via ibis JOINs.
    The database engine performs the expansion at execution time.
    """
    include_parts: list[Table] = []
    exclude_parts: list[Table] = []

    for item in concept_set.items:
        if item.concept_id is None:
            continue

        direct: tuple[int, ...] = (int(item.concept_id),)

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

    if len(include_parts) == 1:
        result = include_parts[0]
    else:
        result = include_parts[0]
        for part in include_parts[1:]:
            result = result.union(part, distinct=False)

    result = result.distinct()

    for e in exclude_parts:
        marked = e.mutate(_cm=ibis.literal(1, type="int64"))
        result = result.join(marked, result.concept_id == marked.concept_id, how="left")
        result = result.filter(result._cm.isnull()).drop("_cm")

    return result.select(result.concept_id.name(CONCEPT_ID))


def _union_all_tables(tables: list[Table]) -> Table:
    """Union multiple single-column ibis tables using binary-tree merge."""
    if not tables:
        raise ValueError("_union_all_tables requires at least one table")
    if len(tables) == 1:
        return tables[0]
    mid = len(tables) // 2
    left = _union_all_tables(tables[:mid])
    right = _union_all_tables(tables[mid:])
    return left.union(right, distinct=False)


def _needs_vocabulary_expansion(concept_sets: Mapping[int, NormalizedConceptSet]) -> bool:
    for cset in concept_sets.values():
        for item in cset.items:
            if item.include_descendants or item.include_mapped:
                return True
    return False


def build_batch_codeset_table(
    *,
    backend: IbisBackendLike,
    concept_sets: Mapping[int, NormalizedConceptSet],
    batch_table_name: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    temporary: bool = False,
) -> Table:
    """Build a ``(codeset_id, concept_id)`` table from multiple concept sets."""
    return build_single_codeset_table(
        backend=backend,
        concept_sets=concept_sets,
        batch_table_name=batch_table_name,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
    )


def _table_getter_from_backend(
    backend: IbisBackendLike,
    schema: str,
) -> Callable[[str, str | None], Table]:
    def _getter(table_name: str, table_schema: str | None) -> Table:
        try:
            if table_schema is not None:
                return backend.table(table_name, database=table_schema)
        except TypeError:
            pass
        return backend.table(table_name)

    return _getter


def _read_table(
    backend: IbisBackendLike,
    *,
    table_name: str,
    schema: str | None,
) -> Table:
    try:
        if schema is not None:
            return backend.table(table_name, database=schema)
    except TypeError:
        pass
    return backend.table(table_name)


def _extract_column(result: Any, col_name: str) -> tuple[int, ...]:
    if hasattr(result, "columns"):
        values = result[col_name].tolist() if col_name in result.columns else result.iloc[:, 0].tolist()
    elif isinstance(result, (list, tuple, set)):
        values = list(result)
    else:
        values = [result] if result is not None else []
    return tuple(int(v) for v in values if v is not None)


def _drop_table(
    backend: IbisBackendLike,
    table_name: str,
    schema: str | None,
) -> None:
    with contextlib.suppress(Exception):
        backend.drop_table(table_name, database=schema, force=True)


def build_single_codeset_table(
    *,
    backend: IbisBackendLike,
    concept_sets: Mapping[int, NormalizedConceptSet],
    batch_table_name: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
) -> Table:
    """Build a per-cohort codeset temp table ``(codeset_id, concept_id)``.

    Like the Java ``#Codesets`` table: a per-cohort temp table populated
    with concept set IDs, used by criteria via JOIN, then dropped.
    """
    if not concept_sets:
        empty = ibis.memtable(
            {"codeset_id": [], "concept_id": []},
            schema={"codeset_id": "int64", "concept_id": "int64"},
        )
        _create_table_impl(
            backend, table_name=batch_table_name, schema=results_schema, obj=empty, overwrite=True, temp=True
        )
        return _read_table(backend, table_name=batch_table_name, schema=results_schema)

    needs_vocab = _needs_vocabulary_expansion(concept_sets)

    if not needs_vocab:
        rows: list[dict[str, Any]] = []
        for cid, cset in concept_sets.items():
            for item in cset.items:
                if not item.is_excluded and item.concept_id is not None:
                    rows.append({"codeset_id": int(cid), "concept_id": int(item.concept_id)})
        data = (
            ibis.memtable(rows, schema={"codeset_id": "int64", "concept_id": "int64"})
            if rows
            else ibis.memtable(
                {"codeset_id": [], "concept_id": []}, schema={"codeset_id": "int64", "concept_id": "int64"}
            )
        )
        _create_table_impl(
            backend, table_name=batch_table_name, schema=results_schema, obj=data, overwrite=True, temp=True
        )
        return _read_table(backend, table_name=batch_table_name, schema=results_schema)

    table_getter = _table_getter_from_backend(backend, vocabulary_schema or "")

    parts: list[Table] = []
    for cid, cset in concept_sets.items():
        if not cset.items:
            continue
        has_vocab = any(item.include_descendants or item.include_mapped for item in cset.items)
        if has_vocab:
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
                    parts.append(
                        ibis.memtable(
                            [{"codeset_id": int(cid), "concept_id": int(item.concept_id)}],
                            schema={"codeset_id": "int64", "concept_id": "int64"},
                        )
                    )

    if not parts:
        empty = ibis.memtable(
            {"codeset_id": [], "concept_id": []}, schema={"codeset_id": "int64", "concept_id": "int64"}
        )
        _create_table_impl(
            backend, table_name=batch_table_name, schema=results_schema, obj=empty, overwrite=True, temp=True
        )
        return _read_table(backend, table_name=batch_table_name, schema=results_schema)

    combined = _union_all_tables(parts)
    _create_table_impl(
        backend, table_name=batch_table_name, schema=results_schema, obj=combined, overwrite=True, temp=True
    )
    return _read_table(backend, table_name=batch_table_name, schema=results_schema)


def drop_codeset_table(
    backend: IbisBackendLike,
    *,
    batch_table_name: str,
    results_schema: str | None = None,
) -> None:
    _drop_table(backend, batch_table_name, results_schema)


def _filter_by_concept_table(
    table: Table,
    concept_table: Table,
    *,
    column: str,
    exclude: bool = False,
) -> Table:
    """Semi-join (include) or anti-join (exclude) *table* against *concept_table*."""
    if not exclude:
        joined = table.join(concept_table, table[column] == concept_table.concept_id)
        return joined.select(*[joined[c] for c in table.columns])
    else:
        marked = concept_table.mutate(_cm=ibis.literal(1, type="int64"))
        joined = table.join(marked, table[column] == marked.concept_id, how="left")
        filtered = joined.filter(joined._cm.isnull())
        return filtered.select(*[filtered[c] for c in table.columns])
