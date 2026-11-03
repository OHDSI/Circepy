"""Shared-checkpoint execution: correctness oracle + performance gate."""

from __future__ import annotations

import time

import pytest

from circe.cohort_definition_set import CohortDefinitionSet, generate_cohort_set
from circe.cohortdefinition import (
    CohortExpression,
    CollapseSettings,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    DateOffsetStrategy,
    InclusionRule,
    Period,
    PrimaryCriteria,
    ResultLimit,
)
from circe.execution.shared import (
    SharedCohortExecutor,
    build_shared_execution_plan,
)
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

COHORT_COLUMNS = ["cohort_definition_id", "subject_id", "cohort_start_date", "cohort_end_date"]


# ---------------------------------------------------------------------------
# Fixtures and expression builders
# ---------------------------------------------------------------------------


def _concept_set(set_id: int, concept_id: int, name: str | None = None) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        name=name,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def _rule(name: str, set_id: int) -> InclusionRule:
    return InclusionRule(
        name=name,
        expression=CriteriaGroup(
            type="ALL",
            criteria_list=[CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=set_id))],
        ),
    )


def _group(set_id: int) -> CriteriaGroup:
    return CriteriaGroup(
        type="ALL",
        criteria_list=[CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=set_id))],
    )


def _expression(
    *,
    ids: tuple[int, int, int] = (1, 2, 3),
    primary_codeset_id: int | None = None,
    primary_repeats: int = 1,
    additional: CriteriaGroup | None = None,
    rules: list[InclusionRule] | None = None,
    qualified_limit: ResultLimit | None = None,
    expression_limit: ResultLimit | None = None,
    end_strategy=None,
    censoring: list | None = None,
    censor_window: Period | None = None,
    collapse: CollapseSettings | None = None,
    title: str | None = None,
) -> CohortExpression:
    condition_id, rule_two_id, rule_three_id = ids
    return CohortExpression(
        concept_sets=[
            _concept_set(condition_id, 111, "entry"),
            _concept_set(rule_two_id, 222, "rule two"),
            _concept_set(rule_three_id, 333, "rule three"),
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                ConditionOccurrence(codeset_id=primary_codeset_id or condition_id)
                for _ in range(primary_repeats)
            ]
        ),
        additional_criteria=additional,
        inclusion_rules=rules or [],
        qualified_limit=qualified_limit,
        expression_limit=expression_limit,
        end_strategy=end_strategy,
        censoring_criteria=censoring or [],
        censor_window=censor_window,
        collapse_settings=collapse,
        title=title,
    )


def _family(size: int) -> CohortDefinitionSet:
    """A refinement-heavy family covering every supported operator."""
    cohort_set = CohortDefinitionSet()
    for index in range(size):
        rules = []
        if index % 2 == 1:
            rules.append(_rule(f"r222_{index}", 2))
        if index % 3 == 0:
            rules.append(_rule(f"r333_{index}", 3))

        additional = _group(3) if index % 4 == 0 else None
        qualified_limit = ResultLimit(type="first") if additional is not None and index % 8 == 0 else None
        expression_limit = (
            ResultLimit(type="first")
            if index % 5 == 0
            else ResultLimit(type="last")
            if index % 7 == 0
            else None
        )
        end_strategy = (
            DateOffsetStrategy(date_field="StartDate", offset=(index % 5) + 1) if index % 6 == 0 else None
        )
        censoring = [ConditionOccurrence(codeset_id=2)] if index % 9 == 0 else []
        censor_window = Period(start_date="2009-01-01", end_date="2019-12-31") if censoring else None
        collapse = CollapseSettings(era_pad=index % 3) if index % 10 == 0 else None

        cohort_set.add(
            cohort_id=index + 1,
            cohort_name=f"cohort {index}",
            expression=_expression(
                additional=additional,
                rules=rules,
                qualified_limit=qualified_limit,
                expression_limit=expression_limit,
                end_strategy=end_strategy,
                censoring=censoring,
                censor_window=censor_window,
                collapse=collapse,
                title=f"cohort {index}",
            ),
        )
    return cohort_set


def _seed_conn(ibis_module, person_count: int = 2000):
    conn = ibis_module.duckdb.connect()
    person_ids = list(range(1, person_count + 1))

    conn.create_table(
        "person",
        obj=ibis_module.memtable(
            {
                "person_id": person_ids,
                "year_of_birth": [1950 + (person_id % 50) for person_id in person_ids],
                "gender_concept_id": [8507 if person_id % 2 else 8532 for person_id in person_ids],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis_module.memtable(
            {
                "person_id": person_ids,
                "observation_period_id": person_ids,
                "observation_period_start_date": ["2000-01-01"] * person_count,
                "observation_period_end_date": ["2020-12-31"] * person_count,
            }
        ),
        overwrite=True,
    )

    rows: dict[str, list] = {
        "person_id": [],
        "condition_occurrence_id": [],
        "condition_concept_id": [],
        "condition_start_date": [],
        "condition_end_date": [],
    }
    event_id = 1
    for person_id in person_ids:
        for month, concept_id in enumerate((111, 222, 333), start=1):
            rows["person_id"].append(person_id)
            rows["condition_occurrence_id"].append(event_id)
            rows["condition_concept_id"].append(concept_id)
            rows["condition_start_date"].append(f"2010-{month:02d}-01")
            rows["condition_end_date"].append(f"2010-{month:02d}-01")
            event_id += 1

    conn.create_table("condition_occurrence", obj=ibis_module.memtable(rows), overwrite=True)
    return conn


@pytest.fixture()
def duckdb_conn():
    ibis = pytest.importorskip("ibis")
    pytest.importorskip("duckdb")
    conn = _seed_conn(ibis)
    yield conn
    conn.disconnect()


def _rows(conn, table: str):
    frame = conn.table(table).execute()
    return frame[COHORT_COLUMNS].sort_values(COHORT_COLUMNS).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Planning (no database)
# ---------------------------------------------------------------------------


def test_plan_shares_primary_across_cohort_local_concept_set_ids():
    first = _expression(ids=(1, 2, 3))
    second = _expression(ids=(11, 12, 13), rules=[_rule("r222", 12)])
    third = _expression(ids=(21, 22, 23), rules=[_rule("same content, other name", 22)])

    plan, canonicalizer = build_shared_execution_plan(
        [(1, "first", first), (2, "second", second), (3, "third", third)]
    )

    assert len(plan.primary_nodes) == 1
    assert len(plan.qualified_nodes) == 0
    assert len(plan.rule_nodes) == 1
    assert len(canonicalizer) == 3
    summary = plan.explain()
    assert summary["cohorts"] == 3
    assert summary["primary_scans_saved"] == 2
    assert summary["rule_recomputations_saved"] == 1
    assert "3 cohort(s)" in plan.describe()


def test_plan_captures_invalid_cohorts_without_aborting():
    good = _expression()
    invalid = CohortExpression(concept_sets=[], primary_criteria=None)

    plan, _ = build_shared_execution_plan([(1, "bad", invalid), (2, "good", good)])

    assert plan.cohorts[0].error is not None
    assert plan.cohorts[1].error is None
    assert plan.explain()["failed_cohorts"] == 1


# ---------------------------------------------------------------------------
# Oracle: shared output must be byte-identical to stand-alone output
# ---------------------------------------------------------------------------


def test_shared_rows_identical_to_standalone(duckdb_conn):
    cohort_set = _family(12)

    sequential = generate_cohort_set(
        cohort_set,
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_sequential",
        shared=False,
    )
    shared = generate_cohort_set(
        cohort_set,
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_shared",
        shared=True,
    )

    assert all(result.status == "COMPLETE" for result in sequential)
    assert all(result.status == "COMPLETE" for result in shared)
    assert _rows(duckdb_conn, "cohort_shared").equals(_rows(duckdb_conn, "cohort_sequential"))
    assert len(_rows(duckdb_conn, "cohort_shared")) > 0

    leftovers = [name for name in duckdb_conn.list_tables() if name.startswith("__s_")]
    assert leftovers == []


def test_shared_rows_identical_with_canonicalised_concept_set_ids(duckdb_conn):
    first = _expression(ids=(1, 2, 3))
    second = _expression(ids=(11, 12, 13), rules=[_rule("r222", 12)])
    cohort_set = CohortDefinitionSet()
    cohort_set.add(cohort_id=1, cohort_name="first", expression=first)
    cohort_set.add(cohort_id=2, cohort_name="second", expression=second)

    generate_cohort_set(
        cohort_set, backend=duckdb_conn, cdm_schema="main", cohort_table="cohort_ids_seq", shared=False
    )
    generate_cohort_set(
        cohort_set, backend=duckdb_conn, cdm_schema="main", cohort_table="cohort_ids_shared", shared=True
    )

    assert _rows(duckdb_conn, "cohort_ids_shared").equals(_rows(duckdb_conn, "cohort_ids_seq"))


def test_shared_incremental_second_run_skips(duckdb_conn):
    cohort_set = _family(4)

    first = generate_cohort_set(
        cohort_set,
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_incremental",
        incremental=True,
        shared=True,
    )
    second = generate_cohort_set(
        cohort_set,
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_incremental",
        incremental=True,
        shared=True,
    )

    assert all(result.status == "COMPLETE" for result in first)
    assert all(result.status == "SKIPPED" for result in second)


def test_shared_records_failures_and_continues(duckdb_conn):
    cohort_set = CohortDefinitionSet()
    cohort_set.add(
        cohort_id=1,
        cohort_name="invalid",
        expression=CohortExpression(concept_sets=[], primary_criteria=None),
    )
    cohort_set.add(cohort_id=2, cohort_name="valid", expression=_expression())

    results = generate_cohort_set(
        cohort_set,
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_failures",
        shared=True,
        stop_on_error=False,
    )

    statuses = {result.cohort_id: result.status for result in results}
    assert statuses == {1: "FAILED", 2: "COMPLETE"}
    assert results[0].error is not None


def test_executor_owns_and_drops_its_session_tables(duckdb_conn):
    executor = SharedCohortExecutor(
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_executor",
    )
    executor.plan([(1, "cohort", _expression())])
    executor.write(1)

    assert "1 primary checkpoint" in executor.describe()
    assert _rows(duckdb_conn, "cohort_executor").shape[0] > 0

    executor.close()
    leftovers = [name for name in duckdb_conn.list_tables() if name.startswith("__x_") or "shared_" in name]
    assert leftovers == []


def test_executor_rejects_unknown_cohort(duckdb_conn):
    executor = SharedCohortExecutor(
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_unknown",
        session_prefix="__test_unknown_",
    )
    executor.plan([(1, "cohort", _expression())])

    with pytest.raises(KeyError):
        executor.build(999)
    executor.close()


# ---------------------------------------------------------------------------
# Performance gate
# ---------------------------------------------------------------------------


def test_shared_generation_is_significantly_faster(duckdb_conn):
    cohort_set = _family(24)

    start = time.perf_counter()
    sequential = generate_cohort_set(
        cohort_set,
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_perf_sequential",
        shared=False,
    )
    sequential_seconds = time.perf_counter() - start

    start = time.perf_counter()
    shared = generate_cohort_set(
        cohort_set,
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_perf_shared",
        shared=True,
    )
    shared_seconds = time.perf_counter() - start

    assert all(result.status == "COMPLETE" for result in sequential)
    assert all(result.status == "COMPLETE" for result in shared)
    assert _rows(duckdb_conn, "cohort_perf_shared").equals(_rows(duckdb_conn, "cohort_perf_sequential"))

    # The family shares one primary checkpoint across 24 definitions.  Require a
    # conservative margin so the gate is stable on slow CI machines while still
    # failing if checkpoint reuse regresses.
    speedup = sequential_seconds / shared_seconds
    assert speedup >= 1.5, (
        f"shared execution was not significantly faster: "
        f"sequential={sequential_seconds:.2f}s shared={shared_seconds:.2f}s speedup={speedup:.2f}x"
    )


def test_shared_handles_multiple_primary_populations(duckdb_conn):
    first = _expression()
    second = _expression(primary_codeset_id=2, rules=[_rule("r333", 3)])
    cohort_set = CohortDefinitionSet()
    cohort_set.add(cohort_id=1, cohort_name="first", expression=first)
    cohort_set.add(cohort_id=2, cohort_name="second", expression=second)

    plan, _ = build_shared_execution_plan(
        [(cohort.cohort_id, cohort.cohort_name, cohort.expression) for cohort in cohort_set]
    )
    assert len(plan.primary_nodes) == 2
    assert plan.explain()["primary_scans_saved"] == 0

    generate_cohort_set(
        cohort_set, backend=duckdb_conn, cdm_schema="main", cohort_table="cohort_multi_seq", shared=False
    )
    generate_cohort_set(
        cohort_set, backend=duckdb_conn, cdm_schema="main", cohort_table="cohort_multi_shared", shared=True
    )

    assert _rows(duckdb_conn, "cohort_multi_shared").equals(_rows(duckdb_conn, "cohort_multi_seq"))


def test_shared_matches_standalone_with_duplicate_primary_criteria(duckdb_conn):
    # Duplicate criteria create duplicate primary rows whose event ids may tie.
    # The materialised checkpoint must still produce the same cohort rows.
    cohort_set = CohortDefinitionSet()
    cohort_set.add(
        cohort_id=1,
        cohort_name="duplicates",
        expression=_expression(primary_repeats=3, rules=[_rule("r222", 2)]),
    )

    generate_cohort_set(
        cohort_set, backend=duckdb_conn, cdm_schema="main", cohort_table="cohort_dup_seq", shared=False
    )
    generate_cohort_set(
        cohort_set, backend=duckdb_conn, cdm_schema="main", cohort_table="cohort_dup_shared", shared=True
    )

    assert _rows(duckdb_conn, "cohort_dup_shared").equals(_rows(duckdb_conn, "cohort_dup_seq"))


def test_executor_can_be_used_as_a_context_manager(duckdb_conn):
    with SharedCohortExecutor(
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_context",
    ) as executor:
        executor.plan([(1, "cohort", _expression())])
        executor.write(1)

    leftovers = [name for name in duckdb_conn.list_tables() if name.startswith("__x_") or "shared_" in name]
    assert leftovers == []


def test_plan_skips_empty_inclusion_rules_and_exposes_input_key():
    empty_rule = InclusionRule(
        name="empty",
        expression=CriteriaGroup(type="ALL", criteria_list=[], demographic_criteria_list=[], groups=[]),
    )
    plan, _ = build_shared_execution_plan([(1, "cohort", _expression(rules=[empty_rule]))])

    assert plan.rule_nodes == {}
    assert plan.cohorts[0].rule_keys == ()
    assert plan.cohorts[0].input_key == plan.cohorts[0].primary_key


def test_executor_requires_planning_and_is_idempotent(duckdb_conn):
    executor = SharedCohortExecutor(
        backend=duckdb_conn,
        cdm_schema="main",
        cohort_table="cohort_plan",
        session_prefix="__test_plan_",
    )
    with pytest.raises(RuntimeError):
        executor.explain()
    with pytest.raises(RuntimeError):
        executor.build(1)

    first = executor.plan([(1, "cohort", _expression())])
    second = executor.plan([(2, "other", _expression())])
    assert first is second
    assert len(second.cohorts) == 1
    executor.close()
