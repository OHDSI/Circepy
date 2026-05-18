from __future__ import annotations

import ibis
import pytest

from circe.execution.ibis.codesets import build_single_codeset_table
from circe.execution.ibis.context import ExecutionContext, make_execution_context


def _make_codeset_table(backend):
    return build_single_codeset_table(
        backend=backend,
        concept_sets={},
        batch_table_name="__test_codesets",
    )


def test_make_execution_context_uses_cdm_schema_as_vocabulary_fallback():
    ibis_mod = pytest.importorskip("ibis")
    conn = ibis_mod.duckdb.connect()
    codeset_table = _make_codeset_table(conn)

    ctx = make_execution_context(
        backend=conn,
        cdm_schema="main",
        codeset_table=codeset_table,
    )

    assert isinstance(ctx, ExecutionContext)
    assert ctx.vocabulary_schema == "main"

    conn.drop_table("__test_codesets", force=True)


def test_make_execution_context_honors_vocabulary_schema_option():
    ibis_mod = pytest.importorskip("ibis")
    conn = ibis_mod.duckdb.connect()
    codeset_table = _make_codeset_table(conn)

    ctx = make_execution_context(
        backend=conn,
        cdm_schema="cdm",
        codeset_table=codeset_table,
        vocabulary_schema="vocab",
    )

    assert ctx.vocabulary_schema == "vocab"

    conn.drop_table("__test_codesets", force=True)


def test_codeset_table_returns_filtered_view():
    ibis_mod = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis_mod.duckdb.connect()
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {
                "concept_id": [111, 222],
                "invalid_reason": [None, None],
            }
        ),
        overwrite=True,
    )

    concept_sets = {
        1: ibis_mod.execution.normalize.cohort.NormalizedConceptSet(
            set_id=1,
            items=(
                ibis_mod.execution.normalize.cohort.NormalizedConceptSetItem(
                    concept_id=111, is_excluded=False
                ),
            ),
        ),
    }

    codeset_table = build_single_codeset_table(
        backend=conn,
        concept_sets=concept_sets,
        batch_table_name="__test_codesets2",
    )

    ctx = make_execution_context(
        backend=conn,
        cdm_schema="main",
        codeset_table=codeset_table,
    )

    # concept_set_table should filter by codeset_id
    filtered = ctx.concept_set_table(1).execute()
    assert len(filtered) == 1
    assert list(filtered["concept_id"]) == [111]

    conn.drop_table("__test_codesets2", force=True)
