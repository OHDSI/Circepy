from __future__ import annotations

import pytest

from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.execution import ExecutionOptions, IbisExecutor, build_ibis
from circe.execution.compat import write_cohort as legacy_write_cohort
from circe.execution.errors import ExecutionError
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def _expression() -> CohortExpression:
    return CohortExpression(
        concept_sets=[_make_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
    )


def _seed_tables(conn, ibis) -> None:
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "year_of_birth": [1980, 1982],
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
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "condition_occurrence_id": [100, 101],
                "condition_concept_id": [111, 111],
                "condition_start_date": ["2020-01-01", "2020-01-02"],
                "condition_end_date": ["2020-01-01", "2020-01-02"],
            }
        ),
        overwrite=True,
    )


def test_legacy_build_helpers_return_relations():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)
    options = ExecutionOptions(cdm_schema="main")

    relation = build_ibis(_expression(), conn, options)

    assert hasattr(relation, "execute")
    assert len(relation.execute()) == 2


def test_legacy_executor_build_matches_function_wrapper():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)
    options = ExecutionOptions(cdm_schema="main")

    executor = IbisExecutor(conn, options)
    via_executor = executor.build(_expression()).execute()
    via_function = build_ibis(_expression(), conn, options).execute()

    assert len(via_executor) == len(via_function) == 2
    assert set(via_executor.person_id) == {1, 2}
    assert executor.captured_sql() == []


def test_legacy_write_cohort_projects_ohdsi_columns():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    legacy_write_cohort(
        _expression(),
        conn,
        table="cohort_legacy",
        schema="main",
        overwrite=True,
        cohort_id=77,
        options=ExecutionOptions(cdm_schema="main"),
    )

    result = conn.table("cohort_legacy", database="main").execute()

    assert list(result.columns) == [
        "cohort_definition_id",
        "subject_id",
        "cohort_start_date",
        "cohort_end_date",
    ]
    assert set(result["cohort_definition_id"]) == {77}
    assert set(result["subject_id"]) == {1, 2}


def test_legacy_executor_write_uses_options_cohort_id_default():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    executor = IbisExecutor(
        conn,
        ExecutionOptions(cdm_schema="main", result_schema="main", cohort_id=91),
    )
    executor.write(_expression(), table="cohort_from_executor", overwrite=True)

    result = conn.table("cohort_from_executor", database="main").execute()
    assert set(result["cohort_definition_id"]) == {91}


def test_legacy_executor_write_requires_cohort_id():
    executor = IbisExecutor(object(), ExecutionOptions())

    with pytest.raises(ExecutionError, match="cohort_id is required"):
        executor.write(_expression(), table="cohort_out", overwrite=True)


def test_legacy_append_raises_if_existing_table_cannot_be_read(monkeypatch: pytest.MonkeyPatch):
    import circe.execution.api as execution_api
    import circe.execution.compat as compat_module

    class _AppendBackend:
        def list_tables(self, database=None):
            return ["cohort_out"]

        def table(self, name, database=None):
            raise RuntimeError("boom")

    monkeypatch.setattr(execution_api, "build_cohort", lambda *args, **kwargs: object())
    monkeypatch.setattr(compat_module, "project_to_ohdsi_cohort_table", lambda relation, cohort_id: relation)

    executor = IbisExecutor(
        _AppendBackend(),
        ExecutionOptions(cdm_schema="main", result_schema="main", cohort_id=7),
    )

    with pytest.raises(ExecutionError, match="failed reading existing table 'cohort_out' for append"):
        executor.write(_expression(), table="cohort_out", append=True, overwrite=False)
