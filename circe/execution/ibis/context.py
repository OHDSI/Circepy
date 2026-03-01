from __future__ import annotations

from dataclasses import field
from typing import Any, Mapping

from .._dataclass import frozen_slots_dataclass
from ..normalize.cohort import NormalizedConceptSet
from .codesets import ConceptSetResolver


@frozen_slots_dataclass
class ExecutionContext:
    backend: Any
    cdm_schema: str
    results_schema: str | None
    vocabulary_schema: str | None
    options: Any
    concept_sets: Mapping[int, NormalizedConceptSet]
    _resolved_codesets: dict[int, tuple[int, ...]] = field(default_factory=dict)

    def table(self, table_name: str) -> Any:
        return self._table_from_schema(table_name, self.cdm_schema)

    def vocabulary_table(self, table_name: str) -> Any:
        return self._table_from_schema(
            table_name,
            self.vocabulary_schema or self.cdm_schema,
        )

    def _table_from_schema(self, table_name: str, schema: str | None) -> Any:
        try:
            if schema is not None:
                return self.backend.table(table_name, database=schema)
        except TypeError:
            pass
        return self.backend.table(table_name)

    def concept_ids_for_codeset(self, codeset_id: int) -> tuple[int, ...]:
        normalized_id = int(codeset_id)
        if normalized_id in self._resolved_codesets:
            return self._resolved_codesets[normalized_id]

        resolver = ConceptSetResolver(
            table_getter=self._table_from_schema,
            vocabulary_schema=self.vocabulary_schema or self.cdm_schema,
            concept_sets=self.concept_sets,
        )
        concept_ids = resolver.resolve_codeset(normalized_id)
        self._resolved_codesets[normalized_id] = concept_ids
        return concept_ids
