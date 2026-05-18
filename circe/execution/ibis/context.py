from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import ibis

from .._dataclass import frozen_slots_dataclass
from ..normalize.cohort import NormalizedConceptSet
from ..typing import IbisBackendLike, Table


def _table_with_schema_fallback(
    backend: IbisBackendLike,
    table_name: str,
    schema: str | None,
) -> Table:
    try:
        if schema is not None:
            return backend.table(table_name, database=schema)
    except TypeError:
        pass
    return backend.table(table_name)


@frozen_slots_dataclass
class ExecutionContext:
    backend: IbisBackendLike
    cdm_schema: str
    results_schema: str | None
    vocabulary_schema: str | None
    codeset_table: Table

    def table(self, table_name: str) -> Table:
        return self._table_from_schema(table_name, self.cdm_schema)

    def vocabulary_table(self, table_name: str) -> Table:
        return self._table_from_schema(
            table_name,
            self.vocabulary_schema or self.cdm_schema,
        )

    def _table_from_schema(self, table_name: str, schema: str | None) -> Table:
        return _table_with_schema_fallback(self.backend, table_name, schema)

    def concept_set_table(self, codeset_id: int) -> Table:
        """Return an ibis Table with a single 'concept_id' column for this codeset.

        References the database-resident batch codeset table.  No Python memory
        is used for concept IDs -- filtering happens via SQL joins at execution time.
        """
        return (
            self.codeset_table.filter(self.codeset_table.codeset_id == codeset_id)
            .select("concept_id")
            .distinct()
        )


def _build_codeset_memtable(
    concept_sets: Mapping[int, NormalizedConceptSet],
) -> Table:
    """Build a simple memtable for concept sets with known concept IDs.

    Only handles simple includes (no descendant/mapped expansion needed).
    This is a fallback for backward-compatible test usage.
    """
    rows: list[dict[str, Any]] = []
    for cid, cset in concept_sets.items():
        for item in cset.items:
            if not item.is_excluded and item.concept_id is not None:
                rows.append({"codeset_id": int(cid), "concept_id": int(item.concept_id)})
    if rows:
        return ibis.memtable(rows, schema={"codeset_id": "int64", "concept_id": "int64"})
    return ibis.memtable(
        {"codeset_id": [], "concept_id": []},
        schema={"codeset_id": "int64", "concept_id": "int64"},
    )


def make_execution_context(
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    codeset_table: Table | None = None,
    concept_sets: Mapping[int, NormalizedConceptSet] | None = None,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
) -> ExecutionContext:
    """Construct an executor context from API-level wiring arguments.

    Provide *codeset_table* (preferred) for a database-resident codeset
    table, or *concept_sets* for backward-compatible single-cohort use.
    """
    vocabulary_schema = vocabulary_schema or cdm_schema

    if codeset_table is None:
        codeset_table = _build_codeset_memtable(concept_sets or {})

    return ExecutionContext(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        codeset_table=codeset_table,
    )
