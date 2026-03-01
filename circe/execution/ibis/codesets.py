from __future__ import annotations

from typing import Any, Callable, Mapping

from ..errors import CompilationError
from ..normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem


TableGetter = Callable[[str, str | None], Any]


class ConceptSetResolver:
    """Resolve concept sets to concrete concept IDs using vocabulary tables."""

    def __init__(
        self,
        *,
        table_getter: TableGetter,
        vocabulary_schema: str | None,
        concept_sets: Mapping[int, NormalizedConceptSet],
    ) -> None:
        self._table_getter = table_getter
        self._vocabulary_schema = vocabulary_schema
        self._concept_sets = concept_sets

    def resolve_codeset(self, codeset_id: int) -> tuple[int, ...]:
        concept_set = self._concept_sets.get(int(codeset_id))
        if concept_set is None or not concept_set.items:
            return ()

        include_ids: set[int] = set()
        exclude_ids: set[int] = set()
        for item in concept_set.items:
            expanded = self._expand_item(item)
            if item.is_excluded:
                exclude_ids.update(expanded)
            else:
                include_ids.update(expanded)

        return tuple(sorted(include_ids - exclude_ids))

    def _expand_item(self, item: NormalizedConceptSetItem) -> set[int]:
        base_ids: set[int] = {int(item.concept_id)}
        if item.include_descendants:
            base_ids.update(self._descendant_ids(base_ids))

        expanded = set(base_ids)
        if item.include_mapped:
            expanded.update(self._mapped_ids(base_ids))
        return expanded

    def _vocabulary_table(self, table_name: str):
        try:
            return self._table_getter(table_name, self._vocabulary_schema)
        except Exception as exc:  # pragma: no cover - backend specific error types
            raise CompilationError(
                f"Failed to access vocabulary table '{table_name}'."
            ) from exc

    def _descendant_ids(self, ancestor_ids: set[int]) -> set[int]:
        if not ancestor_ids:
            return set()

        concept = self._vocabulary_table("concept")
        concept_ancestor = self._vocabulary_table("concept_ancestor")
        query = (
            concept_ancestor.join(
                concept,
                concept_ancestor.descendant_concept_id == concept.concept_id,
            )
            .filter(concept_ancestor.ancestor_concept_id.isin(tuple(ancestor_ids)))
            .filter(concept.invalid_reason.isnull())
            .select(concept_ancestor.descendant_concept_id.name("concept_id"))
            .distinct()
        )
        return self._execute_concept_id_query(query)

    def _mapped_ids(self, input_ids: set[int]) -> set[int]:
        if not input_ids:
            return set()

        concept_relationship = self._vocabulary_table("concept_relationship")
        query = (
            concept_relationship.filter(concept_relationship.concept_id_2.isin(tuple(input_ids)))
            .filter(concept_relationship.relationship_id == "Maps to")
            .filter(concept_relationship.invalid_reason.isnull())
            .select(concept_relationship.concept_id_1.name("concept_id"))
            .distinct()
        )
        return self._execute_concept_id_query(query)

    def _execute_concept_id_query(self, query) -> set[int]:
        try:
            rows = query.execute()
        except Exception as exc:  # pragma: no cover - backend specific error types
            raise CompilationError("Failed executing concept set expansion query.") from exc

        values: list[Any]
        if hasattr(rows, "columns"):  # pandas DataFrame
            if "concept_id" in rows.columns:
                values = rows["concept_id"].tolist()
            else:
                values = rows.iloc[:, 0].tolist()
        elif isinstance(rows, (list, tuple, set)):
            values = list(rows)
        else:
            values = [rows]

        output: set[int] = set()
        for value in values:
            if value is None:
                continue
            output.add(int(value))
        return output
