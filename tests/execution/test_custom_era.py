from __future__ import annotations

from datetime import date

import pytest

from circe.api import build_cohort
from circe.cohortdefinition import (
    CohortExpression,
    ConditionOccurrence,
    DrugExposure,
    PrimaryCriteria,
)
from circe.cohortdefinition.core import CustomEraStrategy, ResultLimit
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(
            items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]
        ),
    )


def _seed_common_tables(conn, ibis):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "year_of_birth": [1980],
                "gender_concept_id": [8507],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "observation_period_id": [10],
                "observation_period_start_date": [date(2019, 1, 1)],
                "observation_period_end_date": [date(2021, 12, 31)],
            }
        ),
        overwrite=True,
    )


def test_custom_era_merges_drugs_within_gap():
    """Drug exposures within gap_days merge into one era; cohort end_date reflects it."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)

    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 1],
                "drug_exposure_id": [1, 2],
                "drug_concept_id": [222, 222],
                "drug_exposure_start_date": [date(2020, 1, 1), date(2020, 2, 1)],
                "drug_exposure_end_date": [date(2020, 1, 31), date(2020, 3, 3)],
                "days_supply": [0, 0],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [100],
                "condition_concept_id": [111],
                "condition_start_date": [date(2020, 1, 1)],
                "condition_end_date": [date(2020, 1, 1)],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            _make_concept_set(1, 111),
            _make_concept_set(2, 222),
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)]
        ),
        end_strategy=CustomEraStrategy(drug_codeset_id=2, gap_days=30, offset=0),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    assert len(result) == 1
    assert str(result.iloc[0]["start_date"])[:10] == "2020-01-01"
    # exp 1: end=2020-01-31, exp 2: end=2020-03-03
    # gap = 1 <= 30 -> merged era: start=2020-01-01, end=2020-03-03
    assert str(result.iloc[0]["end_date"])[:10] == "2020-03-03"


def test_custom_era_no_merge_across_large_gap():
    """Drug exposures beyond gap_days form separate eras; cohort uses nearest era."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)

    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 1],
                "drug_exposure_id": [1, 2],
                "drug_concept_id": [222, 222],
                "drug_exposure_start_date": [date(2020, 1, 1), date(2020, 2, 1)],
                "drug_exposure_end_date": [date(2020, 1, 6), date(2020, 3, 3)],
                "days_supply": [0, 0],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [100],
                "condition_concept_id": [111],
                "condition_start_date": [date(2020, 1, 1)],
                "condition_end_date": [date(2020, 1, 1)],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            _make_concept_set(1, 111),
            _make_concept_set(2, 222),
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)]
        ),
        end_strategy=CustomEraStrategy(drug_codeset_id=2, gap_days=5, offset=0),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    assert len(result) == 1
    assert str(result.iloc[0]["start_date"])[:10] == "2020-01-01"
    # exp 1: end=2020-01-06, exp 2: end=2020-03-03
    # gap = 26 > 5 -> separate eras
    # cohort start 2020-01-01 matches era 1: end 2020-01-06
    assert str(result.iloc[0]["end_date"])[:10] == "2020-01-06"


def test_custom_era_offset_applied():
    """Offset days are added to the drug era end_date."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)

    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "drug_exposure_id": [1],
                "drug_concept_id": [222],
                "drug_exposure_start_date": [date(2020, 1, 1)],
                "drug_exposure_end_date": [date(2020, 1, 10)],
                "days_supply": [0],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [100],
                "condition_concept_id": [111],
                "condition_start_date": [date(2020, 1, 1)],
                "condition_end_date": [date(2020, 1, 1)],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            _make_concept_set(1, 111),
            _make_concept_set(2, 222),
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)]
        ),
        end_strategy=CustomEraStrategy(drug_codeset_id=2, gap_days=30, offset=7),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    assert len(result) == 1
    assert str(result.iloc[0]["start_date"])[:10] == "2020-01-01"
    # drug effective end: 2020-01-10 (end_date override)
    # era: start=2020-01-01, end=2020-01-10+7=2020-01-17
    assert str(result.iloc[0]["end_date"])[:10] == "2020-01-17"


def test_custom_era_no_matching_drugs():
    """No matching drug exposures -> fall back to observation_period_end_date."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)

    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [100],
                "condition_concept_id": [111],
                "condition_start_date": [date(2020, 1, 15)],
                "condition_end_date": [date(2020, 1, 15)],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [],
                "drug_exposure_id": [],
                "drug_concept_id": [],
                "drug_exposure_start_date": [],
                "drug_exposure_end_date": [],
                "days_supply": [],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            _make_concept_set(1, 111),
            _make_concept_set(2, 999),
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)]
        ),
        end_strategy=CustomEraStrategy(drug_codeset_id=2, gap_days=30, offset=0),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    assert len(result) == 1
    assert str(result.iloc[0]["start_date"])[:10] == "2020-01-15"
    # No matching drugs -> end_date = observation_period_end_date = 2021-12-31
    assert str(result.iloc[0]["end_date"])[:10] == "2021-12-31"


def test_custom_era_with_drug_exposure_as_primary():
    """Custom era works with DrugExposure as the primary criterion."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)

    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 1],
                "drug_exposure_id": [1, 2],
                "drug_concept_id": [222, 222],
                "drug_exposure_start_date": [date(2020, 1, 1), date(2020, 2, 1)],
                "drug_exposure_end_date": [date(2020, 1, 31), date(2020, 3, 3)],
                "days_supply": [0, 0],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 222)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[DrugExposure(codeset_id=1)]
        ),
        end_strategy=CustomEraStrategy(drug_codeset_id=1, gap_days=30, offset=0),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    # With primary_limit_type="all", both drug exposures produce cohort entries.
    # Both entries get end_date from the merged drug era (2020-03-03).
    assert len(result) == 2
    start_dates = sorted(result["start_date"].astype(str).tolist())
    assert start_dates == ["2020-01-01", "2020-02-01"]
    assert all(
        str(d)[:10] == "2020-03-03" for d in result["end_date"]
    )


def test_compute_drug_eras_matches_java_sql_logic():
    """compute_drug_eras ibis output matches equivalent raw SQL (Java template translated to DuckDB)."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    from types import SimpleNamespace

    from circe.execution.engine.custom_era import compute_drug_eras

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)

    # 5 exposures for person 1, with gap_days=7, offset=3.
    # Exposure end_dates are set explicitly so COALESCE is predictable.
    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1, 1, 1],
                "drug_exposure_id": [1, 2, 3, 4, 5],
                "drug_concept_id": [222, 222, 222, 222, 222],
                "drug_exposure_start_date": [
                    date(2020, 1, 1),
                    date(2020, 1, 10),
                    date(2020, 3, 1),
                    date(2020, 3, 20),
                    date(2020, 5, 1),
                ],
                "drug_exposure_end_date": [
                    date(2020, 1, 6),
                    date(2020, 2, 9),
                    date(2020, 3, 21),
                    date(2020, 3, 30),
                    date(2020, 5, 15),
                ],
                "days_supply": [0, 0, 0, 0, 0],
            }
        ),
        overwrite=True,
    )

    ctx = SimpleNamespace(
        table=lambda name: conn.table(name),
        concept_ids_for_codeset=lambda cid: (222,) if cid == 2 else (),
    )

    # --- ibis path ---
    ibis_result = compute_drug_eras(
        ctx, drug_codeset_id=2, gap_days=7, offset=3, days_supply_override=None
    ).execute()
    ibis_result = ibis_result.sort_values(["person_id", "era_start_date"]).reset_index(drop=True)

    # --- raw SQL path (Java template core logic, DuckDB dialect) ---
    # Java template uses: COALESCE(end, start+days_supply, start+1)
    # then pads by (gap_days + offset), groups by cumulative-max-over-preceding,
    # and finally subtracts gap_days from max(end) to leave only offset.
    gap = 7
    off = 3

    sql = f"""
    WITH exposures AS (
        SELECT
            person_id::INTEGER AS person_id,
            drug_exposure_start_date::DATE AS start_date,
            COALESCE(
                drug_exposure_end_date::DATE,
                drug_exposure_start_date::DATE + days_supply::INTEGER,
                drug_exposure_start_date::DATE + 1
            ) + {gap + off} AS padded_end
        FROM drug_exposure
        WHERE drug_concept_id IN (222)
    ),
    with_prev_max AS (
        SELECT *,
            MAX(padded_end) OVER (
                PARTITION BY person_id ORDER BY start_date, padded_end DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ) AS prev_max
        FROM exposures
    ),
    with_markers AS (
        SELECT *,
            CASE WHEN prev_max IS NULL OR prev_max < start_date THEN 1 ELSE 0 END AS is_new
        FROM with_prev_max
    ),
    with_era AS (
        SELECT *,
            SUM(is_new) OVER (
                PARTITION BY person_id
                ORDER BY start_date, is_new DESC, padded_end DESC
            ) AS era_id
        FROM with_markers
    )
    SELECT
        person_id,
        MIN(start_date)::DATE AS era_start_date,
        (MAX(padded_end) - {gap})::DATE AS era_end_date
    FROM with_era
    GROUP BY person_id, era_id
    ORDER BY person_id, MIN(start_date)
    """

    raw_conn = conn.con
    sql_result = raw_conn.sql(sql).fetchdf()

    # --- compare ---
    pd = pytest.importorskip("pandas")
    pd.testing.assert_frame_equal(
        ibis_result,
        sql_result,
        check_dtype=False,
        check_column_type=False,
    )


def test_full_cohort_custom_era_matches_sql_end_dates():
    """Full cohort pipeline with CustomEraStrategy produces same end_dates as raw SQL."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)

    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 1],
                "drug_exposure_id": [1, 2],
                "drug_concept_id": [222, 222],
                "drug_exposure_start_date": [date(2020, 1, 1), date(2020, 2, 1)],
                "drug_exposure_end_date": [date(2020, 1, 31), date(2020, 3, 3)],
                "days_supply": [0, 0],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [100],
                "condition_concept_id": [111],
                "condition_start_date": [date(2020, 1, 1)],
                "condition_end_date": [date(2020, 1, 1)],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            _make_concept_set(1, 111),
            _make_concept_set(2, 222),
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)]
        ),
        end_strategy=CustomEraStrategy(drug_codeset_id=2, gap_days=30, offset=0),
    )

    # --- ibis pipeline ---
    cohort_result = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    # --- raw SQL pipeline (Java CUSTOM_ERA_STRATEGY_TEMPLATE logic, DuckDB dialect) ---
    # Computes drug eras, then matches era end_dates to events via start_date overlap.
    sql = f"""
    WITH drug_eras AS (
        SELECT
            person_id,
            MIN(start_date) AS era_start_date,
            MAX(padded_end) - 30 AS era_end_date
        FROM (
            SELECT
                person_id, start_date, padded_end,
                SUM(is_new) OVER (
                    PARTITION BY person_id
                    ORDER BY start_date, is_new DESC, padded_end DESC
                ) AS era_id
            FROM (
                SELECT
                    person_id, start_date, padded_end,
                    CASE WHEN prev_max IS NULL OR prev_max < start_date THEN 1 ELSE 0 END AS is_new
                FROM (
                    SELECT
                        person_id, start_date, padded_end,
                        MAX(padded_end) OVER (
                            PARTITION BY person_id ORDER BY start_date, padded_end DESC
                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                        ) AS prev_max
                    FROM (
                        SELECT
                            de.person_id,
                            de.drug_exposure_start_date::DATE AS start_date,
                            COALESCE(
                                de.drug_exposure_end_date::DATE,
                                de.drug_exposure_start_date::DATE + de.days_supply::INTEGER,
                                de.drug_exposure_start_date::DATE + 1
                            ) + 30 AS padded_end
                        FROM drug_exposure de
                        WHERE de.drug_concept_id = 222
                    ) raw_ends
                ) maxes
            ) marked
        ) indexed
        GROUP BY person_id, era_id
    ),
    events_with_obs AS (
        SELECT
            e.person_id,
            e.condition_occurrence_id AS event_id,
            e.condition_start_date::DATE AS start_date,
            op.observation_period_end_date::DATE AS op_end_date
        FROM condition_occurrence e
        JOIN observation_period op ON e.person_id = op.person_id
    )
    SELECT
        ev.person_id,
        ev.start_date,
        LEAST(
            COALESCE(MAX(er.era_end_date), ev.op_end_date),
            ev.op_end_date
        )::DATE AS end_date
    FROM events_with_obs ev
    LEFT JOIN drug_eras er
        ON ev.person_id = er.person_id
        AND ev.start_date BETWEEN er.era_start_date AND er.era_end_date
    GROUP BY ev.person_id, ev.event_id, ev.start_date, ev.op_end_date
    ORDER BY ev.person_id, ev.start_date
    """

    sql_result = conn.con.sql(sql).fetchdf()

    # Compare end_dates and start_dates after sorting
    ibis_ends = sorted(cohort_result["end_date"].astype(str).tolist())
    sql_ends = sorted(sql_result["end_date"].astype(str).tolist())
    assert ibis_ends == sql_ends

    ibis_starts = sorted(cohort_result["start_date"].astype(str).tolist())
    sql_starts = sorted(sql_result["start_date"].astype(str).tolist())
    assert ibis_starts == sql_starts


# ---------------------------------------------------------------------------
# Regression: CustomEra must preserve all events when event_id is shared
#
# After ``first=True`` + ``QualifiedLimit=First`` + ``ExpressionLimit=First``
# every person contributes at most one event, and ``_assign_primary_event_ids``
# assigns ``event_id=1`` to all of them.  The CustomEra window that selects
# one matching era per event must therefore partition on *(person_id, event_id)*
# — otherwise all rows collapse into a single partition and only one survives.
# ---------------------------------------------------------------------------


def _seed_common_tables_multi_person(conn, ibis):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "year_of_birth": [1980, 1985, 1990],
                "gender_concept_id": [8507, 8507, 8507],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "observation_period_id": [10, 11, 12],
                "observation_period_start_date": [date(2019, 1, 1), date(2019, 1, 1), date(2019, 1, 1)],
                "observation_period_end_date": [date(2021, 12, 31), date(2021, 12, 31), date(2021, 12, 31)],
            }
        ),
        overwrite=True,
    )


def test_custom_era_preserves_all_persons_with_first_true():
    """All persons survive when DrugExposure(first=True) + CustomEra + limits.

    The window ``group_by=joined.event_id`` previously collapsed every row
    into a single partition because all events had ``event_id=1`` (assigned
    by ``_assign_primary_event_ids`` — each person has exactly 1 event after
    ``first=True`` and the per-person limits).
    """
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables_multi_person(conn, ibis)

    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "drug_exposure_id": [100, 200, 300],
                "drug_concept_id": [222, 222, 222],
                "drug_exposure_start_date": [date(2020, 1, 1), date(2020, 2, 1), date(2020, 3, 1)],
                "drug_exposure_end_date": [date(2020, 1, 31), date(2020, 2, 28), date(2020, 3, 31)],
                "days_supply": [0, 0, 0],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 222)],
        primary_criteria=PrimaryCriteria(criteria_list=[DrugExposure(codeset_id=1, first=True)]),
        qualified_limit=ResultLimit(Type="First"),
        expression_limit=ResultLimit(Type="First"),
        end_strategy=CustomEraStrategy(drug_codeset_id=1, gap_days=30, offset=0),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    assert len(result) == 3, f"expected 3 rows, got {len(result)}"
    assert set(result["person_id"]) == {1, 2, 3}
