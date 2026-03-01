from __future__ import annotations

from circe.cohortdefinition import BuildExpressionQueryOptions
from circe.execution.ibis.codesets import CachedConceptSetResolver
from circe.execution.ibis.context import ExecutionContext, make_execution_context


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
        options=None,
    )

    assert isinstance(ctx, ExecutionContext)
    assert ctx.vocabulary_schema == "cdm"
    assert isinstance(ctx.codeset_resolver, CachedConceptSetResolver)
    assert ctx.table("person") == ("person", "cdm")
    assert ctx.concept_ids_for_codeset(999) == ()


def test_make_execution_context_honors_vocabulary_schema_option_and_backend_fallback():
    backend = _BackendWithoutSchemaSupport()
    options = BuildExpressionQueryOptions()
    options.vocabulary_schema = "vocab"
    ctx = make_execution_context(
        backend=backend,
        cdm_schema="cdm",
        concept_sets={},
        options=options,
    )

    assert ctx.vocabulary_schema == "vocab"
    assert ctx.vocabulary_table("concept") == ("concept", None)
    assert backend.calls == [("concept", "vocab"), ("concept", None)]
