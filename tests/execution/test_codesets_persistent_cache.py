from __future__ import annotations

import pytest

from circe.execution.ibis.codesets import build_batch_codeset_table
from circe.execution.normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem


def test_build_batch_codeset_table_round_trip():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {
                "concept_id": [111, 222, 333],
                "invalid_reason": ["X", None, None],
            },
            schema={"concept_id": "int64", "invalid_reason": "string"},
        ),
        overwrite=True,
    )

    concept_sets = {
        1: NormalizedConceptSet(
            set_id=1,
            items=(
                NormalizedConceptSetItem(
                    concept_id=111, is_excluded=False, include_descendants=False, include_mapped=False
                ),
            ),
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
