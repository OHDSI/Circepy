import pytest

from circe.api import evaluate_cohort
from circe.evaluation.builder import EvaluationBuilder


def _seed_common_tables(conn, ibis):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "year_of_birth": [1980, 2015],
                "gender_concept_id": [8507, 8507],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "observation_period_id": [10, 11],
                "observation_period_start_date": ["2019-01-01", "2019-01-01"],
                "observation_period_end_date": ["2021-12-31", "2021-12-31"],
            }
        ),
        overwrite=True,
    )


def _seed_vocabulary_tables(conn, ibis):
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {
                "concept_id": [111, 222, 999],
                "invalid_reason": [None, None, None],
            }
        ).mutate(invalid_reason=ibis._.invalid_reason.cast("string")),
        overwrite=True,
    )
    conn.create_table(
        "concept_ancestor",
        obj=ibis.memtable(
            {
                "ancestor_concept_id": [111, 222],
                "descendant_concept_id": [111, 222],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept_relationship",
        obj=ibis.memtable(
            {
                "concept_id_1": [111, 222],
                "concept_id_2": [111, 222],
                "relationship_id": ["Maps to", "Maps to"],
                "invalid_reason": [None, None],
            }
        ).mutate(invalid_reason=ibis._.invalid_reason.cast("string")),
        overwrite=True,
    )


def test_evaluate_cohort_with_ibis():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    _seed_vocabulary_tables(conn, ibis)

    # Create condition occurrence
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 2],
                "condition_occurrence_id": [100, 101, 102],
                "condition_concept_id": [111, 222, 999],
                "condition_start_date": ["2020-01-01", "2020-02-01", "2020-01-05"],
                "condition_end_date": ["2020-01-02", "2020-02-02", "2020-01-06"],
            }
        ),
        overwrite=True,
    )

    # Mock index events table
    # Standard format has person_id, start_date, end_date, event_id
    index_events = ibis.memtable(
        {
            "person_id": [1, 2],
            "start_date": ["2020-01-15", "2020-01-15"],
            "end_date": ["2020-01-15", "2020-01-15"],
            "event_id": [1, 2],
            "cohort_definition_id": [99, 99],
            "visit_occurrence_id": [0, 0],
        }
    ).mutate(
        start_date=ibis._.start_date.cast("date"),
        end_date=ibis._.end_date.cast("date"),
    )

    with EvaluationBuilder("Test Rubric") as ev:
        cs_111 = ev.concept_set("Condition 111", 111)
        cs_222 = ev.concept_set("Condition 222", 222)
        ev.add_rule("Has Condition 111", weight=10.0).condition(cs_111)
        ev.add_rule("Has Condition 222 within 30 days before", weight=5.0).condition(
            cs_222
        ).within_days_before(30)

    rubric = ev.rubric

    eval_table = evaluate_cohort(
        rubric=rubric,
        index_events=index_events,
        ruleset_id=42,
        backend=conn,
        cdm_schema="main",
        include_cohort_id=True,
    )

    result = eval_table.execute()

    assert "ruleset_id" in result.columns
    assert "cohort_definition_id" in result.columns
    assert "subject_id" in result.columns
    assert "index_date" in result.columns
    assert "rule_id" in result.columns
    assert "score" in result.columns

    # Person 1 has condition 111 and condition 222
    # Condition 111 is on 2020-01-01 (before 2020-01-15) => matched
    # Condition 222 is on 2020-02-01 (after 2020-01-15) => not within 30 days BEFORE
    # Wait, the rule Has Condition 111 evaluates for ALL time by default?
    # Actually, default occurrence is "any time prior to or on index date"?
    # CIRCE correlated criteria: if no window is specified, it checks anytime.

    # Filter for Person 1
    p1_results = result[result["subject_id"] == 1]

    # Should have a score for Rule 1 (Has Condition 111)
    rule_1_id = rubric.rules[0].rule_id
    assert len(p1_results[p1_results["rule_id"] == rule_1_id]) == 1

    # Person 2 has no 111 or 222 condition
    p2_results = result[result["subject_id"] == 2]
    assert len(p2_results) == 0
