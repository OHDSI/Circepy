from __future__ import annotations

from collections.abc import Mapping

from .._dataclass import frozen_slots_dataclass
from ..normalize.cohort import NormalizedConceptSet
from ..typing import IbisBackendLike, Table
from .codesets import CachedConceptSetResolver


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
    codeset_resolver: CachedConceptSetResolver

    def table(self, table_name: str) -> Table:
        return self._table_from_schema(table_name, self.cdm_schema)

    def vocabulary_table(self, table_name: str) -> Table:
        return self._table_from_schema(
            table_name,
            self.vocabulary_schema or self.cdm_schema,
        )

    def _table_from_schema(self, table_name: str, schema: str | None) -> Table:
        return _table_with_schema_fallback(self.backend, table_name, schema)

    def concept_ids_for_codeset(self, codeset_id: int) -> tuple[int, ...]:
        return self.codeset_resolver.resolve_codeset(codeset_id)


def make_execution_context(
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    concept_sets: Mapping[int, NormalizedConceptSet],
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    use_persistent_cache: bool = False,
) -> ExecutionContext:
    """Construct an executor context from API-level wiring arguments."""
    vocabulary_schema = vocabulary_schema or cdm_schema

    def _table_getter(table_name: str, schema: str | None) -> Table:
        return _table_with_schema_fallback(backend, table_name, schema)

    resolver = CachedConceptSetResolver(
        table_getter=_table_getter,
        vocabulary_schema=vocabulary_schema,
        concept_sets=concept_sets,
        backend=backend if use_persistent_cache else None,
        results_schema=results_schema if use_persistent_cache else None,
        use_persistent_cache=use_persistent_cache,
    )
    return ExecutionContext(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        codeset_resolver=resolver,
    )
