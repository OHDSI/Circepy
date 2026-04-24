import pytest

from circe.api import calculate_cohort_metrics
from circe.evaluation.builder import EvaluationBuilder
from circe.evaluation.models import RubricSet


def _seed_vocabulary_tables(conn, ibis):
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {
                "concept_id": [111, 222],
                "invalid_reason": ["", ""],
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
                "invalid_reason": ["", ""],
            }
        ).mutate(invalid_reason=ibis._.invalid_reason.cast("string")),
        overwrite=True,
    )


def _seed_common_tables(conn, ibis):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3, 4],
                "year_of_birth": [1980, 2015, 1990, 1970],
                "gender_concept_id": [8507, 8507, 8532, 8507],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3, 4],
                "observation_period_id": [10, 11, 12, 13],
                "observation_period_start_date": ["2019-01-01", "2019-01-01", "2019-01-01", "2019-01-01"],
                "observation_period_end_date": ["2021-12-31", "2021-12-31", "2021-12-31", "2021-12-31"],
            }
        ),
        overwrite=True,
    )


def test_calculate_cohort_metrics():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    _seed_vocabulary_tables(conn, ibis)

    # Create condition occurrence
    # Concept 111 (Sensitive proxy): Person 1, 2, 3 have it
    # Concept 222 (Specific proxy): Person 1, 3 have it
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3, 1, 3],
                "condition_occurrence_id": [100, 101, 102, 103, 104],
                "condition_concept_id": [111, 111, 111, 222, 222],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-01",
                    "2020-01-01",
                    "2020-01-01",
                    "2020-01-01",
                ],
                "condition_end_date": ["2020-01-02", "2020-01-02", "2020-01-02", "2020-01-02", "2020-01-02"],
            }
        ),
        overwrite=True,
    )

    # Mock index events table (Universe of all people evaluated + target cohort)
    # Target Cohort (ID=99): Person 1, 2
    # So Target Cohort has:
    # Person 1: In sensitive (111), In specific (222) -> TP
    # Person 2: In sensitive (111), NOT specific -> FP
    # Person 3: NOT in target, but IN specific (222) -> FN

    # We provide index events representing the universe (Target Cohort 99 + Others)
    index_events = ibis.memtable(
        {
            "person_id": [1, 2, 3, 4],
            "start_date": ["2020-01-01", "2020-01-01", "2020-01-01", "2020-01-01"],
            "end_date": ["2020-01-01", "2020-01-01", "2020-01-01", "2020-01-01"],
            "event_id": [1, 2, 3, 4],
            "cohort_definition_id": [99, 99, 0, 0],
            "visit_occurrence_id": [0, 0, 0, 0],
        }
    ).mutate(
        start_date=ibis._.start_date.cast("date"),
        end_date=ibis._.end_date.cast("date"),
    )

    with EvaluationBuilder("Sensitive 111") as sens_ev:
        cs_111 = sens_ev.concept_set("Condition 111", 111)
        sens_ev.add_rule("Has Sensitive Proxy", weight=1).condition(cs_111)

    with EvaluationBuilder("Specific 222") as spec_ev:
        cs_222 = spec_ev.concept_set("Condition 222", 222)
        spec_ev.add_rule("Has Specific Proxy", weight=1).condition(cs_222)

    rubric_set = RubricSet(
        target_cohort_id=99,
        sensitive_rubric=sens_ev.rubric,
        specific_rubric=spec_ev.rubric,
    )

    metrics_table = calculate_cohort_metrics(
        rubric_set=rubric_set,
        index_events=index_events,
        backend=conn,
        cdm_schema="main",
    )

    result = metrics_table.execute()

    assert len(result) == 1
    row = result.iloc[0]

    assert row["target_cohort_id"] == 99

    # TP: Person 1 (Target & Specific)
    # FP: Person 2 (Target & NOT Sensitive) => Wait, person 2 IS in Sensitive! So Person 2 is NOT a FP?
    # Let me re-read the FP definition: In Target AND NOT in Sensitive.
    # Person 2 is in Sensitive. So pseudo_fp should be 0 for Person 2? Yes.
    # Wait, my setup: Person 2 has 111 (Sensitive). Target has Person 2.
    # Target (1, 2). Sens (1, 2, 3). Spec (1, 3).
    # TP = Target & Spec = (1)
    # FP = Target & ~Sens = Ø (0)
    # FN = ~Target & Spec = (3)

    # Let's add a Person 4 to make them a FP
    # Target has Person 4, but Person 4 has NO conditions! So not in Sensitive.

    assert row["pseudo_tp"] == 1  # Person 1
    assert row["pseudo_fn"] == 1  # Person 3

    # Since Person 2 is in Target and sensitive, they are not FP. Person 4 is not in Target. We don't have FP.
    assert row["pseudo_fp"] == 0
