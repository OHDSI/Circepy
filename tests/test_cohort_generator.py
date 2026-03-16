"""Tests for hash-based cohort generator orchestration."""

from __future__ import annotations

import pytest

from circe.execution import (
    CohortDefinitionMember,
    CohortDefinitionSet,
    CohortGenerator,
    ExecutionOptions,
    InMemoryRegistry,
    compute_definition_hash,
    compute_set_hash,
)
from circe.execution.registry import CohortRunRecord, utc_now



@pytest.fixture
def duckdb_conn():
    """Create an in-memory DuckDB connection with basic CDM tables."""
    pytest.importorskip("duckdb")
    ibis = pytest.importorskip("ibis")

    conn = ibis.duckdb.connect()

    # Create vocabulary tables needed for cohort building
    conn.create_table(
        "concept",
        obj=ibis.memtable({
            "concept_id": [201826, 4329847],
            "concept_name": ["Type 2 diabetes mellitus", "Myocardial infarction"],
            "invalid_reason": [None, None],  # OK to use None here based on test_execution_api.py
        }),
        overwrite=True,
    )

    conn.create_table(
        "concept_ancestor",
        obj=ibis.memtable({
            "ancestor_concept_id": [201826, 4329847],
            "descendant_concept_id": [201826, 4329847],
        }),
        overwrite=True,
    )

    conn.create_table(
        "concept_relationship",
        obj=ibis.memtable({
            "concept_id_1": [201826],
            "concept_id_2": [201826],
            "relationship_id": ["Maps to"],
            "invalid_reason": [""],  # Empty string to avoid NULL-typed column
        }),
        overwrite=True,
    )

    # Create condition_occurrence table for cohort criteria (with all required columns)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable({
            "person_id": [1, 2, 3],
            "condition_occurrence_id": [1001, 1002, 1003],
            "condition_concept_id": [201826, 4329847, 201826],
            "condition_start_date": ["2021-01-15", "2021-02-20", "2021-03-10"],
            "condition_end_date": ["2021-01-15", "2021-02-20", "2021-03-10"],
        }),
        overwrite=True,
    )

    return conn


@pytest.fixture
def ibis_executor(duckdb_conn):
    """Create an IbisExecutor with a DuckDB connection."""
    from circe.execution import IbisExecutor

    options = ExecutionOptions()
    executor = IbisExecutor(duckdb_conn, options)
    yield executor
    executor.close()


def _simple_cohort_expression(title: str, concept_id: int = 201826) -> dict:
    """Create a simple cohort expression for testing."""
    return {
        "Title": title,
        "ConceptSets": [
            {
                "id": 0,
                "name": "Test Concept",
                "expression": {
                    "items": [
                        {
                            "concept": {
                                "CONCEPT_ID": concept_id,
                                "CONCEPT_NAME": "Test",
                                "VOCABULARY_ID": "SNOMED",
                            }
                        }
                    ]
                },
            }
        ],
        "PrimaryCriteria": {
            "CriteriaList": [
                {
                    "ConditionOccurrence": {
                        "CodesetId": 0,
                    }
                }
            ],
            "ObservationWindow": {
                "PriorDays": 0,
                "PostDays": 0,
            },
            "PrimaryCriteriaLimit": {"Type": "All"},
        },
        "QualifiedLimit": {"Type": "First"},
        "ExpressionLimit": {"Type": "All"},
        "InclusionRules": [],
        "EndStrategy": {
            "DateOffset": {
                "DateField": "EndDate",
                "Offset": 0,
            }
        },
        "CensoringCriteria": [],
        "CollapseSettings": {
            "CollapseType": "ERA",
            "EraPad": 0,
        },
        "CensorWindow": {},
    }


def test_definition_hash_is_stable_for_equivalent_inputs():
    left = compute_definition_hash({"Title": "A", "ConceptSets": []})
    right = compute_definition_hash({"ConceptSets": [], "Title": "A"})
    assert left == right


def test_set_hash_is_order_insensitive_for_members():
    first = CohortDefinitionSet(
        set_id="set-1",
        set_name="demo",
        cohorts=[
            CohortDefinitionMember(cohort_id=2, name="b", expression=_simple_cohort_expression("B", 4329847)),
            CohortDefinitionMember(cohort_id=1, name="a", expression=_simple_cohort_expression("A", 201826)),
        ],
    )
    second = CohortDefinitionSet(
        set_id="set-1",
        set_name="demo",
        cohorts=[
            CohortDefinitionMember(cohort_id=1, name="a", expression=_simple_cohort_expression("A", 201826)),
            CohortDefinitionMember(cohort_id=2, name="b", expression=_simple_cohort_expression("B", 4329847)),
        ],
    )
    assert compute_set_hash(first) == compute_set_hash(second)


def test_generate_first_run_executes_and_records_success(ibis_executor, duckdb_conn):
    generator = CohortGenerator(ibis_executor, InMemoryRegistry())

    expression = _simple_cohort_expression("Test Cohort A", 201826)
    result = generator.generate(expression, cohort_id=100, table="cohort")

    assert result.status == "success"
    assert result.executed is True
    assert result.row_count is not None
    # Verify the cohort table was created
    assert "cohort" in duckdb_conn.list_tables()


def test_generate_skips_when_hash_matches_prior_success(ibis_executor):
    registry = InMemoryRegistry()
    generator = CohortGenerator(ibis_executor, registry)

    expression = _simple_cohort_expression("Test Cohort A", 201826)
    definition_hash = compute_definition_hash(expression)
    registry.upsert_cohort_run(
        CohortRunRecord(
            cohort_id=1,
            definition_hash=definition_hash,
            status="success",
            target_schema=None,
            target_table="cohort",
            run_id="run-1",
            started_at=utc_now(),
            row_count=42,
            finished_at=utc_now(),
        )
    )

    result = generator.generate(expression, cohort_id=1, table="cohort", incremental=True)

    assert result.status == "skipped"
    assert result.executed is False


def test_generate_raises_when_prior_run_is_still_running(ibis_executor):
    registry = InMemoryRegistry()
    generator = CohortGenerator(ibis_executor, registry, running_timeout_seconds=120)

    registry.upsert_cohort_run(
        CohortRunRecord(
            cohort_id=5,
            definition_hash="old",
            status="running",
            target_schema=None,
            target_table="cohort",
            run_id="run-live",
            started_at=utc_now(),
        )
    )

    with pytest.raises(RuntimeError, match="already has a running execution"):
        generator.generate(_simple_cohort_expression("new"), cohort_id=5, table="cohort")


def test_generate_records_failure_status(ibis_executor):
    registry = InMemoryRegistry()
    generator = CohortGenerator(ibis_executor, registry)

    # Use an invalid/malformed expression to trigger a failure
    invalid_expression = {"Title": "Invalid", "ConceptSets": "not_a_list"}  # This should fail
    result = generator.generate(invalid_expression, cohort_id=9, table="cohort")
    record = registry.get_cohort_run(9)

    assert result.status == "failed"
    assert result.error_message is not None
    assert record is not None
    assert record.status == "failed"


def test_generate_set_supports_remove_missing_and_short_circuit(ibis_executor):
    registry = InMemoryRegistry()
    generator = CohortGenerator(ibis_executor, registry)

    set_v1 = CohortDefinitionSet(
        set_id="alpha",
        set_name="Alpha",
        cohorts=[
            CohortDefinitionMember(cohort_id=10, expression=_simple_cohort_expression("A", 201826)),
            CohortDefinitionMember(cohort_id=20, expression=_simple_cohort_expression("B", 4329847)),
        ],
    )
    first = generator.generate_set(set_v1, table="cohort")
    assert first.status == "success"

    set_v2 = CohortDefinitionSet(
        set_id="alpha",
        set_name="Alpha",
        cohorts=[CohortDefinitionMember(cohort_id=10, expression=_simple_cohort_expression("A", 201826))],
    )
    second = generator.generate_set(set_v2, table="cohort", remove_missing=True)
    assert second.removed_cohort_ids == [20]

    third = generator.generate_set(
        set_v2,
        table="cohort",
        short_circuit_on_unchanged_set=True,
    )
    assert third.status == "skipped"


def test_different_sets_with_shared_cohort_ids_skip_unchanged_cohorts(ibis_executor, duckdb_conn):
    """
    Demonstrates the key insight: per-cohort hashes are tracked independently.
    If the same cohort_id appears in two different sets with the same expression,
    the second set will skip re-execution of that cohort (per-cohort incremental).
    """
    registry = InMemoryRegistry()
    generator = CohortGenerator(ibis_executor, registry)

    # Set 1: cohorts A and B
    set_alpha = CohortDefinitionSet(
        set_id="set-alpha",
        set_name="Alpha Set",
        cohorts=[
            CohortDefinitionMember(cohort_id=100, name="cohort_a", expression=_simple_cohort_expression("A", 201826)),
            CohortDefinitionMember(cohort_id=101, name="cohort_b", expression=_simple_cohort_expression("B", 4329847)),
        ],
    )
    result_alpha = generator.generate_set(set_alpha, table="cohort")
    assert result_alpha.status == "success"
    assert len(result_alpha.cohort_results) == 2
    # Both cohorts should have executed
    assert all(r.executed for r in result_alpha.cohort_results)

    # Set 2: shares cohort 100 (cohort_a) with same expression, plus new cohort 102
    set_beta = CohortDefinitionSet(
        set_id="set-beta",
        set_name="Beta Set",
        cohorts=[
            CohortDefinitionMember(cohort_id=100, name="cohort_a", expression=_simple_cohort_expression("A", 201826)),
            CohortDefinitionMember(cohort_id=102, name="cohort_c", expression=_simple_cohort_expression("C", 201826)),
        ],
    )
    result_beta = generator.generate_set(set_beta, table="cohort")
    assert result_beta.status == "success"
    assert len(result_beta.cohort_results) == 2

    # Cohort 100 should be skipped (incremental, same cohort_id + same expression hash)
    cohort_100_result = [r for r in result_beta.cohort_results if r.cohort_id == 100][0]
    assert cohort_100_result.executed is False
    assert cohort_100_result.skipped is True
    assert cohort_100_result.status == "skipped"

    # Cohort 102 should be executed (first time seeing this cohort_id)
    cohort_102_result = [r for r in result_beta.cohort_results if r.cohort_id == 102][0]
    assert cohort_102_result.executed is True
    assert cohort_102_result.skipped is False



