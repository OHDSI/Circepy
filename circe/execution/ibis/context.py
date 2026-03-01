from __future__ import annotations

from typing import Any, Mapping

from .._dataclass import frozen_slots_dataclass


@frozen_slots_dataclass
class ExecutionContext:
    backend: Any
    cdm_schema: str
    results_schema: str | None
    options: Any
    concept_sets: Mapping[int, frozenset[int]]

    def table(self, table_name: str) -> Any:
        try:
            return self.backend.table(table_name, database=self.cdm_schema)
        except TypeError:
            return self.backend.table(table_name)

    def concept_ids_for_codeset(self, codeset_id: int) -> tuple[int, ...]:
        concept_ids = self.concept_sets.get(int(codeset_id), frozenset())
        return tuple(sorted(concept_ids))
