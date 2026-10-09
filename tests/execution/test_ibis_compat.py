from __future__ import annotations

import pytest

from circe.execution.ibis_compat import literal_column_relation, literal_rows_relation


def test_literal_column_relation_round_trips_values():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    relation = literal_column_relation(
        [3, 1, 2],
        column_name="value",
        dtype="int64",
        backend=conn,
    )
    result = relation.execute()

    assert sorted(result["value"].tolist()) == [1, 2, 3]


def test_literal_column_relation_empty_preserves_schema():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    relation = literal_column_relation(
        [],
        column_name="value",
        dtype="int64",
        backend=conn,
    )
    result = relation.execute()

    assert list(result.columns) == ["value"]
    assert len(result) == 0


def test_literal_rows_relation_round_trips_typed_rows():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    relation = literal_rows_relation(
        [
            {"cohort_id": 1, "cohort_name": "A", "is_subset": False},
            {"cohort_id": 2, "cohort_name": None, "is_subset": True},
        ],
        schema={
            "cohort_id": "int64",
            "cohort_name": "string",
            "is_subset": "boolean",
        },
        backend=conn,
    )
    result = relation.execute().sort_values("cohort_id").reset_index(drop=True)

    assert list(result["cohort_id"]) == [1, 2]
    assert result.loc[0, "cohort_name"] == "A"
    assert result.loc[1, "cohort_name"] is None or result["cohort_name"].isna().iloc[1]
    assert list(result["is_subset"]) == [False, True]


def test_literal_rows_relation_empty_relation():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    relation = literal_rows_relation(
        [],
        schema={"cohort_id": "int64", "status": "string"},
        backend=conn,
    )
    result = relation.execute()

    assert list(result.columns) == ["cohort_id", "status"]
    assert len(result) == 0
