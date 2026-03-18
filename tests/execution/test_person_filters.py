from __future__ import annotations

import pytest

from circe.execution.errors import CompilationError
from circe.execution.ibis.person_filters import (
    _apply_numeric_predicate,
    apply_person_age_filter,
    apply_person_ethnicity_filter,
    apply_person_gender_filter,
    apply_person_race_filter,
)
from circe.execution.plan.predicates import NumericRangePredicate


class _PersonFilterContext:
    def __init__(self, conn, *, codesets: dict[int, tuple[int, ...]] | None = None):
        self.conn = conn
        self.codesets = codesets or {}

    def table(self, name: str):
        return self.conn.table(name)

    def concept_ids_for_codeset(self, codeset_id: int) -> tuple[int, ...]:
        return self.codesets.get(codeset_id, ())


def _seed_person_tables(conn, ibis):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "year_of_birth": [1980, 1995, 2005],
                "gender_concept_id": [8507, 8532, 8507],
                "race_concept_id": [8527, 8516, 8527],
                "ethnicity_concept_id": [38003564, 38003563, 38003564],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "events",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "start_date": ["2020-01-01", "2020-01-01", "2020-01-01"],
            }
        ),
        overwrite=True,
    )


def test_apply_person_age_filter_supports_between_predicate():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_person_tables(conn, ibis)
    ctx = _PersonFilterContext(conn)
    events = conn.table("events")

    result = apply_person_age_filter(
        events,
        ctx,
        date_column="start_date",
        predicate=NumericRangePredicate(op="between", value=20, extent=40),
    ).execute()

    assert set(result.person_id) == {1, 2}


def test_apply_person_numeric_predicate_rejects_invalid_between_and_op():
    with pytest.raises(CompilationError, match="between' requires an extent value"):
        _apply_numeric_predicate(
            5,
            NumericRangePredicate(op="between", value=1, extent=None),
        )

    with pytest.raises(CompilationError, match="unsupported person numeric range op"):
        _apply_numeric_predicate(
            5,
            NumericRangePredicate(op="invalid", value=1, extent=None),
        )


def test_apply_person_gender_filter_returns_original_table_when_no_ids():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_person_tables(conn, ibis)
    ctx = _PersonFilterContext(conn)
    events = conn.table("events")

    assert apply_person_gender_filter(events, ctx, concept_ids=(), codeset_id=None) is events


def test_apply_person_gender_filter_merges_explicit_and_codeset_ids():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_person_tables(conn, ibis)
    ctx = _PersonFilterContext(conn, codesets={1: (8507, 8532)})
    events = conn.table("events")

    result = apply_person_gender_filter(events, ctx, concept_ids=(8507,), codeset_id=1).execute()

    assert set(result.person_id) == {1, 2, 3}


def test_apply_person_race_and_ethnicity_filters_use_codeset_expansion():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_person_tables(conn, ibis)
    ctx = _PersonFilterContext(conn, codesets={2: (8527,), 3: (38003564,)})
    events = conn.table("events")

    race_result = apply_person_race_filter(events, ctx, concept_ids=(), codeset_id=2).execute()
    ethnicity_result = apply_person_ethnicity_filter(events, ctx, concept_ids=(), codeset_id=3).execute()

    assert set(race_result.person_id) == {1, 3}
    assert set(ethnicity_result.person_id) == {1, 3}
