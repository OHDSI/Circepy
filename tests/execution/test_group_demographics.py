from __future__ import annotations

import pytest

from circe.execution.engine.group_demographics import (
    _apply_date_predicate,
    _demographic_concept_ids,
    demographic_match_keys,
)
from circe.execution.errors import UnsupportedFeatureError
from circe.execution.normalize.groups import NormalizedDemographicCriteria
from circe.execution.normalize.windows import NormalizedDateRange, NormalizedNumericRange


class _DemographicContext:
    def __init__(self, conn, *, codesets: dict[int, tuple[int, ...]] | None = None):
        self.conn = conn
        self.codesets = codesets or {}

    def table(self, name: str):
        return self.conn.table(name)

    def concept_ids_for_codeset(self, codeset_id: int) -> tuple[int, ...]:
        return self.codesets.get(codeset_id, ())


def _seed_demographic_tables(conn, ibis):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "year_of_birth": [1980, 1990, 1980],
                "gender_concept_id": [8507, 8507, 8532],
                "race_concept_id": [8527, 8516, 8527],
                "ethnicity_concept_id": [38003564, 38003564, 38003563],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "index_events",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "event_id": [10, 20, 30],
                "start_date": ["2020-01-05", "2020-02-05", "2020-01-10"],
                "end_date": ["2020-01-20", "2020-02-20", "2020-01-15"],
            }
        ),
        overwrite=True,
    )


def test_apply_date_predicate_rejects_invalid_between_and_op():
    ibis = pytest.importorskip("ibis")

    with pytest.raises(UnsupportedFeatureError, match="between' requires an extent value"):
        _apply_date_predicate(
            ibis.literal("2020-01-01"),
            NormalizedDateRange(op="between", value="2020-01-01", extent=None),
        )

    with pytest.raises(UnsupportedFeatureError, match="unsupported demographic date range op"):
        _apply_date_predicate(
            ibis.literal("2020-01-01"),
            NormalizedDateRange(op="invalid", value="2020-01-01", extent=None),
        )


def test_demographic_concept_ids_merge_codesets_without_duplicates():
    ctx = _DemographicContext(None, codesets={1: (8507, 8532)})

    assert _demographic_concept_ids(explicit_ids=(8507,), codeset_id=1, ctx=ctx) == (8507, 8532)


def test_demographic_match_keys_applies_all_supported_filters():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_demographic_tables(conn, ibis)
    ctx = _DemographicContext(conn, codesets={1: (8507,), 2: (38003564,)})

    demographic = NormalizedDemographicCriteria(
        age=NormalizedNumericRange(op="gte", value=30, extent=None),
        gender_codeset_id=1,
        race_concept_ids=(8527,),
        ethnicity_codeset_id=2,
        occurrence_start_date=NormalizedDateRange(
            op="between",
            value="2020-01-01",
            extent="2020-01-31",
        ),
        occurrence_end_date=NormalizedDateRange(
            op="lte",
            value="2020-01-31",
            extent=None,
        ),
    )

    result = demographic_match_keys(conn.table("index_events"), demographic, ctx).execute()

    assert list(result.person_id) == [1]
    assert list(result.event_id) == [10]
