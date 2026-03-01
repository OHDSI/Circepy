from __future__ import annotations

from typing import Mapping

from ...cohortdefinition import BuildExpressionQueryOptions
from .._dataclass import frozen_slots_dataclass
from ..normalize.cohort import NormalizedConceptSet
from ..typing import BackendLike, Table
from .codesets import CachedConceptSetResolver


@frozen_slots_dataclass
class ExecutionContext:
    backend: BackendLike
    cdm_schema: str
    results_schema: str | None
    vocabulary_schema: str | None
    options: BuildExpressionQueryOptions | None
    concept_sets: Mapping[int, NormalizedConceptSet]
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
