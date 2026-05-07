from __future__ import annotations

import pytest

from circe.execution.ibis.codesets import (
    _CACHE_TABLE_NAME,
    CachedConceptSetResolver,
    _compute_cache_key,
    clear_codeset_cache,
)
from circe.execution.ibis.context import make_execution_context
from circe.execution.normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem

# ------------------------------------------------------------------
# _compute_cache_key tests
# ------------------------------------------------------------------


def _make_items(*specs: tuple[int, bool, bool, bool]) -> tuple[NormalizedConceptSetItem, ...]:
    return tuple(
        NormalizedConceptSetItem(
            concept_id=s[0], is_excluded=s[1], include_descendants=s[2], include_mapped=s[3]
        )
        for s in specs
    )


def test_compute_cache_key_deterministic():
    items = _make_items((1, False, True, False), (2, True, False, True))
    assert _compute_cache_key(items) == _compute_cache_key(items)


def test_compute_cache_key_order_independent():
    items_a = _make_items((1, False, True, False), (2, True, False, True))
    items_b = _make_items((2, True, False, True), (1, False, True, False))
    assert _compute_cache_key(items_a) == _compute_cache_key(items_b)


def test_compute_cache_key_different_items_different_hash():
    items_a = _make_items((1, False, True, False))
    items_b = _make_items((1, False, False, False))
    assert _compute_cache_key(items_a) != _compute_cache_key(items_b)


# ------------------------------------------------------------------
# Persistent cache integration tests using DuckDB
# ------------------------------------------------------------------


@pytest.fixture
def duckdb_backend():
    ibis = pytest.importorskip("ibis")
    backend = ibis.duckdb.connect()
    backend.raw_sql("CREATE SCHEMA results")
    return backend


def _concept_set_fixture():
    return {
        1: NormalizedConceptSet(
            set_id=1,
            items=(
                NormalizedConceptSetItem(
                    concept_id=100,
                    is_excluded=False,
                    include_descendants=False,
                    include_mapped=False,
                ),
            ),
        )
    }


def test_persistent_cache_write_and_read(duckdb_backend, monkeypatch):
    """First resolve writes to persistent cache; second resolver instance reads from it."""
    concept_sets = _concept_set_fixture()

    resolver1 = CachedConceptSetResolver(
        table_getter=lambda name, schema: duckdb_backend.table(name, database=schema),
        vocabulary_schema=None,
        concept_sets=concept_sets,
        backend=duckdb_backend,
        results_schema="results",
        use_persistent_cache=True,
    )

    # Bypass vocabulary expansion — just return the concept_id directly
    monkeypatch.setattr(resolver1, "_expand_item", lambda item: {item.concept_id})

    result = resolver1.resolve_codeset(1)
    assert result == (100,)

    # Verify the cache table was created with data
    cache_tbl = duckdb_backend.table(_CACHE_TABLE_NAME, database="results")
    rows = cache_tbl.execute()
    assert len(rows) == 1

    # Second resolver — _expand_item should NOT be called (persistent cache hit)
    expand_calls = []

    resolver2 = CachedConceptSetResolver(
        table_getter=lambda name, schema: duckdb_backend.table(name, database=schema),
        vocabulary_schema=None,
        concept_sets=concept_sets,
        backend=duckdb_backend,
        results_schema="results",
        use_persistent_cache=True,
    )

    def _expand_should_not_be_called(item):
        expand_calls.append(item.concept_id)
        return {item.concept_id}

    monkeypatch.setattr(resolver2, "_expand_item", _expand_should_not_be_called)

    result2 = resolver2.resolve_codeset(1)
    assert result2 == (100,)
    assert expand_calls == [], "Expected persistent cache hit — _expand_item should not be called"


def test_persistent_cache_disabled_by_default(monkeypatch):
    """Without use_persistent_cache=True, no persistent ops happen."""
    concept_sets = _concept_set_fixture()

    resolver = CachedConceptSetResolver(
        table_getter=lambda name, schema: None,
        vocabulary_schema=None,
        concept_sets=concept_sets,
    )

    monkeypatch.setattr(resolver, "_expand_item", lambda item: {item.concept_id})

    result = resolver.resolve_codeset(1)
    assert result == (100,)
    assert not resolver._use_persistent_cache


def test_persistent_cache_read_failure_falls_back_silently(duckdb_backend, monkeypatch):
    """If cache read raises, expansion still works."""
    concept_sets = _concept_set_fixture()

    resolver = CachedConceptSetResolver(
        table_getter=lambda name, schema: duckdb_backend.table(name, database=schema),
        vocabulary_schema=None,
        concept_sets=concept_sets,
        backend=duckdb_backend,
        results_schema="results",
        use_persistent_cache=True,
    )

    monkeypatch.setattr(resolver, "_expand_item", lambda item: {item.concept_id})

    # Force _read_persistent_cache to encounter an error internally by making
    # table_exists raise. The method catches all exceptions and returns None.
    from circe.execution.ibis import operations as ops

    def _broken_table_exists(*args, **kwargs):
        raise RuntimeError("simulated db failure")

    monkeypatch.setattr(ops, "table_exists", _broken_table_exists)

    result = resolver.resolve_codeset(1)
    assert result == (100,)


def test_clear_codeset_cache(duckdb_backend, monkeypatch):
    """clear_codeset_cache empties the cache table."""
    concept_sets = _concept_set_fixture()

    resolver = CachedConceptSetResolver(
        table_getter=lambda name, schema: duckdb_backend.table(name, database=schema),
        vocabulary_schema=None,
        concept_sets=concept_sets,
        backend=duckdb_backend,
        results_schema="results",
        use_persistent_cache=True,
    )
    monkeypatch.setattr(resolver, "_expand_item", lambda item: {item.concept_id})
    resolver.resolve_codeset(1)

    # Verify rows exist
    cache_tbl = duckdb_backend.table(_CACHE_TABLE_NAME, database="results")
    assert len(cache_tbl.execute()) > 0

    # Clear and verify empty
    clear_codeset_cache(duckdb_backend, "results")
    cache_tbl = duckdb_backend.table(_CACHE_TABLE_NAME, database="results")
    assert len(cache_tbl.execute()) == 0


def test_make_execution_context_threads_persistent_cache():
    """make_execution_context passes persistent cache params to resolver."""
    ibis = pytest.importorskip("ibis")
    backend = ibis.duckdb.connect()

    ctx = make_execution_context(
        backend=backend,
        cdm_schema="main",
        concept_sets={},
        results_schema="main",
        use_persistent_cache=True,
    )

    assert ctx.codeset_resolver._use_persistent_cache is True
    assert ctx.codeset_resolver._backend is backend
    assert ctx.codeset_resolver._results_schema == "main"


def test_make_execution_context_persistent_cache_disabled_without_results_schema():
    """Persistent cache gracefully disabled when results_schema is None."""
    ibis = pytest.importorskip("ibis")
    backend = ibis.duckdb.connect()

    ctx = make_execution_context(
        backend=backend,
        cdm_schema="main",
        concept_sets={},
        results_schema=None,
        use_persistent_cache=True,
    )

    assert ctx.codeset_resolver._use_persistent_cache is False
