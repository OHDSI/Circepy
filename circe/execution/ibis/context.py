from __future__ import annotations

from collections.abc import Mapping

from ...cohortdefinition import BuildExpressionQueryOptions
from .._dataclass import frozen_slots_dataclass
from ..normalize.cohort import NormalizedConceptSet
from ..typing import IbisBackendLike, Table
from .codesets import CachedConceptSetResolver


@frozen_slots_dataclass
class ExecutionContext:
    backend: IbisBackendLike
    cdm_schema: str
    results_schema: str | None
    vocabulary_schema: str | None
    options: BuildExpressionQueryOptions | None
    codeset_resolver: CachedConceptSetResolver

    def table(self, table_name: str) -> Table:
        return self._table_from_schema(table_name, self.cdm_schema)

    def vocabulary_table(self, table_name: str) -> Table:
        return self._table_from_schema(
            table_name,
            self.vocabulary_schema or self.cdm_schema,
        )

    def _table_from_schema(self, table_name: str, schema: str | None) -> Table:
        try:
            if schema is not None:
                return self.backend.table(table_name, database=schema)
        except TypeError:
            pass
        return self.backend.table(table_name)

    def concept_ids_for_codeset(self, codeset_id: int) -> tuple[int, ...]:
        return self.codeset_resolver.resolve_codeset(codeset_id)


def make_execution_context(
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    concept_sets: Mapping[int, NormalizedConceptSet],
    results_schema: str | None = None,
    options: BuildExpressionQueryOptions | None = None,
) -> ExecutionContext:
    """Construct an executor context from API-level wiring arguments."""
    vocabulary_schema = (
        options.vocabulary_schema
        if options is not None and options.vocabulary_schema
        else cdm_schema
    )

    def _table_getter(table_name: str, schema: str | None) -> Table:
        try:
            if schema is not None:
                return backend.table(table_name, database=schema)
        except TypeError:
            pass
        return backend.table(table_name)

    resolver = CachedConceptSetResolver(
        table_getter=_table_getter,
        vocabulary_schema=vocabulary_schema,
        concept_sets=concept_sets,
    )
    return ExecutionContext(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        options=options,
        codeset_resolver=resolver,
    )
