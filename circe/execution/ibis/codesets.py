from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any

from ..errors import CompilationError
from ..normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem
from ..plan.schema import CONCEPT_ID
from ..typing import IbisBackendLike, Table

_CACHE_TABLE_NAME = "_circe_codeset_cache"


def _compute_cache_key(items: tuple[NormalizedConceptSetItem, ...]) -> str:
    """Deterministic SHA-256 hash of sorted concept set items."""
    canonical = sorted(
        (item.concept_id, item.is_excluded, item.include_descendants, item.include_mapped) for item in items
    )
    payload = json.dumps(canonical, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clear_codeset_cache(
    backend: IbisBackendLike,
    results_schema: str | None,
) -> None:
    """Drop the persistent codeset cache table if it exists."""
    from .operations import create_table, table_exists

    if not table_exists(backend, table_name=_CACHE_TABLE_NAME, schema=results_schema):
        return

    import ibis

    empty = ibis.memtable(
        {"cache_key": [], "concept_id": []},
        schema={"cache_key": "string", "concept_id": "int64"},
    )
    create_table(backend, table_name=_CACHE_TABLE_NAME, schema=results_schema, obj=empty, overwrite=True)


class CachedConceptSetResolver:
    """Resolve concept sets to concrete concept IDs using vocabulary tables."""

    def __init__(
        self,
        *,
        table_getter: Callable[[str, str | None], Table],
        vocabulary_schema: str | None,
        concept_sets: Mapping[int, NormalizedConceptSet],
        backend: IbisBackendLike | None = None,
        results_schema: str | None = None,
        use_persistent_cache: bool = False,
    ) -> None:
        self._table_getter = table_getter
        self._vocabulary_schema = vocabulary_schema
        self._concept_sets = concept_sets
        self._cache: dict[int, tuple[int, ...]] = {}
        self._backend = backend
        self._results_schema = results_schema
        self._use_persistent_cache = (
            use_persistent_cache and backend is not None and results_schema is not None
        )
        self._persistent_cache_initialized: bool = False

    def resolve_codeset(self, codeset_id: int) -> tuple[int, ...]:
        normalized_id = int(codeset_id)
        if normalized_id in self._cache:
            return self._cache[normalized_id]

        concept_set = self._concept_sets.get(normalized_id)
        if concept_set is None or not concept_set.items:
            return ()

        # L2: persistent cache lookup
        cache_key: str | None = None
        if self._use_persistent_cache:
            cache_key = _compute_cache_key(concept_set.items)
            persistent_hit = self._read_persistent_cache(cache_key)
            if persistent_hit is not None:
                self._cache[normalized_id] = persistent_hit
                return persistent_hit

        include_ids: set[int] = set()
        exclude_ids: set[int] = set()
        for item in concept_set.items:
            expanded = self._expand_item(item)
            if item.is_excluded:
                exclude_ids.update(expanded)
            else:
                include_ids.update(expanded)

        resolved = tuple(sorted(include_ids - exclude_ids))
        self._cache[normalized_id] = resolved

        # L2: persistent cache write
        if self._use_persistent_cache and cache_key is not None and resolved:
            self._write_persistent_cache(cache_key, resolved)

        return resolved

    def _expand_item(self, item: NormalizedConceptSetItem) -> set[int]:
        base_ids: set[int] = {int(item.concept_id)}
        if item.include_descendants:
            base_ids.update(self._descendant_ids(base_ids))

        expanded = set(base_ids)
        if item.include_mapped:
            expanded.update(self._mapped_ids(base_ids))
        return expanded

    def _vocabulary_table(self, table_name: str) -> Table:
        try:
            return self._table_getter(table_name, self._vocabulary_schema)
        except Exception as exc:  # pragma: no cover - backend specific error types
            raise CompilationError(
                f"Ibis executor compilation error: failed to access vocabulary table '{table_name}'."
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
            .select(concept_ancestor.descendant_concept_id.name(CONCEPT_ID))
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
            .select(concept_relationship.concept_id_1.name(CONCEPT_ID))
            .distinct()
        )
        return self._execute_concept_id_query(query)

    def _execute_concept_id_query(self, query: Table) -> set[int]:
        try:
            rows = query.execute()
        except Exception as exc:  # pragma: no cover - backend specific error types
            raise CompilationError(
                "Ibis executor compilation error: failed executing concept-set expansion query."
            ) from exc

        values: list[Any]
        if hasattr(rows, "columns"):  # pandas DataFrame
            values = rows[CONCEPT_ID].tolist() if CONCEPT_ID in rows.columns else rows.iloc[:, 0].tolist()
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

    # ------------------------------------------------------------------
    # Persistent cache helpers
    # ------------------------------------------------------------------

    def _read_persistent_cache(self, cache_key: str) -> tuple[int, ...] | None:
        from .operations import read_table, table_exists

        try:
            if not table_exists(self._backend, table_name=_CACHE_TABLE_NAME, schema=self._results_schema):
                return None
            tbl = read_table(self._backend, table_name=_CACHE_TABLE_NAME, schema=self._results_schema)
            rows = tbl.filter(tbl.cache_key == cache_key).select("concept_id").execute()
            if hasattr(rows, "columns"):
                values = rows["concept_id"].tolist()
            elif isinstance(rows, (list, tuple)):
                values = list(rows)
            else:
                return None
            if not values:
                return None
            return tuple(sorted(int(v) for v in values if v is not None))
        except Exception:
            return None

    def _write_persistent_cache(self, cache_key: str, concept_ids: tuple[int, ...]) -> None:
        import ibis

        from .operations import create_table, insert_relation, table_exists

        try:
            data = ibis.memtable(
                {"cache_key": [cache_key] * len(concept_ids), "concept_id": list(concept_ids)},
                schema={"cache_key": "string", "concept_id": "int64"},
            )
            if not self._persistent_cache_initialized:
                if not table_exists(self._backend, table_name=_CACHE_TABLE_NAME, schema=self._results_schema):
                    create_table(
                        self._backend,
                        table_name=_CACHE_TABLE_NAME,
                        schema=self._results_schema,
                        obj=data,
                    )
                    self._persistent_cache_initialized = True
                    return
                self._persistent_cache_initialized = True
            insert_relation(
                data,
                backend=self._backend,
                target_table=_CACHE_TABLE_NAME,
                target_schema=self._results_schema,
            )
        except Exception:
            pass
