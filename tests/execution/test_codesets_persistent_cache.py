from __future__ import annotations

import pytest

from circe.execution.ibis.codesets import (
    _CACHE_TABLE_NAME,
    _compute_cache_key,
    build_batch_codeset_table,
    _read_codeset_cache,
    _write_codeset_cache,
)
from circe.execution.normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem


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


def test_build_batch_codeset_table_round_trip():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {
                "concept_id": [111, 222, 333],
                "invalid_reason": [None, None, None],
            }
        ),
        overwrite=True,
    )

    concept_sets = {
        1: NormalizedConceptSet(
            set_id=1,
            items=(NormalizedConceptSetItem(concept_id=111, is_excluded=False),),
        ),
    }

    tbl = build_batch_codeset_table(
        backend=conn,
        concept_sets=concept_sets,
        batch_table_name="__test_codesets",
        vocabulary_schema=None,
    )
    rows = tbl.execute()
    assert set(rows["codeset_id"]) == {1}
    assert set(rows["concept_id"]) == {111}

    conn.drop_table("__test_codesets", force=True)


def test_persistent_cache_write_and_read():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()

    _write_codeset_cache(
        conn, cache_key="testkey", concept_ids=(111, 222), schema=None, table_name=_CACHE_TABLE_NAME
    )

    result = _read_codeset_cache(conn, cache_key="testkey", schema=None, table_name=_CACHE_TABLE_NAME)
    assert result == (111, 222)

    conn.drop_table(_CACHE_TABLE_NAME, force=True)


def test_persistent_cache_miss_returns_none():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()

    result = _read_codeset_cache(conn, cache_key="nonexistent", schema=None, table_name=_CACHE_TABLE_NAME)
    assert result is None
    if conn.exists_table(_CACHE_TABLE_NAME):
        conn.drop_table(_CACHE_TABLE_NAME, force=True)
