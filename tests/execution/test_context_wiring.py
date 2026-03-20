from __future__ import annotations

from types import SimpleNamespace

from circe.execution.ibis.codesets import CachedConceptSetResolver
from circe.execution.ibis.context import ExecutionContext, make_execution_context
from circe.execution.normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem


class _BackendWithSchemaSupport:
    def __init__(self):
        self.calls: list[tuple[str, str | None]] = []

    def table(self, name: str, database: str | None = None):
        self.calls.append((name, database))
        return (name, database)


class _BackendWithoutSchemaSupport:
    def __init__(self):
        self.calls: list[tuple[str, str | None]] = []

    def table(self, name: str, database: str | None = None):
        self.calls.append((name, database))
        if database is not None:
            raise TypeError("database kwarg not supported")
        return (name, None)


def test_make_execution_context_uses_cdm_schema_as_vocabulary_fallback():
    backend = _BackendWithSchemaSupport()
    ctx = make_execution_context(
        backend=backend,
        cdm_schema="cdm",
        concept_sets={},
    )

    assert isinstance(ctx, ExecutionContext)
    assert ctx.vocabulary_schema == "cdm"
    assert isinstance(ctx.codeset_resolver, CachedConceptSetResolver)
    assert ctx.table("person") == ("person", "cdm")
    assert ctx.concept_ids_for_codeset(999) == ()


def test_make_execution_context_honors_vocabulary_schema_option_and_backend_fallback():
    backend = _BackendWithoutSchemaSupport()
    ctx = make_execution_context(
        backend=backend,
        cdm_schema="cdm",
        concept_sets={},
        vocabulary_schema="vocab",
    )

    assert ctx.vocabulary_schema == "vocab"
    assert ctx.vocabulary_table("concept") == ("concept", None)
    assert backend.calls == [("concept", "vocab"), ("concept", None)]


def test_codeset_resolver_caches_expanded_results(monkeypatch):
    resolver = CachedConceptSetResolver(
        table_getter=lambda name, schema: (name, schema),
        vocabulary_schema="vocab",
        concept_sets={
            1: NormalizedConceptSet(
                set_id=1,
                items=(
                    NormalizedConceptSetItem(
                        concept_id=123,
                        is_excluded=False,
                        include_descendants=False,
                        include_mapped=False,
                    ),
                ),
            )
        },
    )
    calls: list[int] = []

    def _expand(item):
        calls.append(item.concept_id)
        return {item.concept_id}

    monkeypatch.setattr(resolver, "_expand_item", _expand)

    assert resolver.resolve_codeset(1) == (123,)
    assert resolver.resolve_codeset(1) == (123,)
    assert calls == [123]


def test_codeset_resolver_handles_empty_and_non_dataframe_query_results():
    resolver = CachedConceptSetResolver(
        table_getter=lambda name, schema: (name, schema),
        vocabulary_schema="vocab",
        concept_sets={},
    )

    assert resolver._descendant_ids(set()) == set()
    assert resolver._mapped_ids(set()) == set()
    assert resolver._execute_concept_id_query(SimpleNamespace(execute=lambda: [1, None, 2])) == {1, 2}
    assert resolver._execute_concept_id_query(SimpleNamespace(execute=lambda: 3)) == {3}
