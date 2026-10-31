#!/usr/bin/env python
"""Benchmark shared-checkpoint execution against stand-alone batch generation.

Builds a synthetic OMOP CDM in DuckDB, generates a refinement-heavy family of
cohort definitions twice (``shared=False`` and ``shared=True``), verifies that
the cohort rows are identical, and reports the speedup.

Example:
    python benchmarks/decomposable_cohorts.py --persons 20000 --cohorts 64
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Allow running from a source checkout without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ibis  # noqa: E402

from circe.cohort_definition_set import (  # noqa: E402
    CohortDefinitionSet,
    generate_cohort_set,
)
from circe.cohortdefinition import (  # noqa: E402
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
from circe.decomposition import decompose_cohort_set  # noqa: E402
from circe.execution.shared import build_shared_execution_plan  # noqa: E402
from circe.vocabulary import (  # noqa: E402
    Concept,
    ConceptSet,
    ConceptSetExpression,
    ConceptSetItem,
)

CONDITION_CONCEPTS = (111, 222, 333, 444, 555)
COHORT_COLUMNS = ["cohort_definition_id", "subject_id", "cohort_start_date", "cohort_end_date"]


def _concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
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
    concept_count: int,
    additional: CriteriaGroup | None,
    rules: list[InclusionRule],
    qualified_limit: ResultLimit | None,
    expression_limit: ResultLimit | None,
    end_strategy,
    censoring: list,
    censor_window: Period | None,
    collapse: CollapseSettings | None,
) -> CohortExpression:
    concept_sets = [
        _concept_set(index + 1, concept_id)
        for index, concept_id in enumerate(CONDITION_CONCEPTS[:concept_count])
    ]
    return CohortExpression(
        concept_sets=concept_sets,
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        additional_criteria=additional,
        inclusion_rules=rules,
        qualified_limit=qualified_limit,
        expression_limit=expression_limit,
        end_strategy=end_strategy,
        censoring_criteria=censoring,
        censor_window=censor_window,
        collapse_settings=collapse,
        title="benchmark cohort",
    )


def build_family(size: int) -> CohortDefinitionSet:
    """A family where every cohort shares the same entry population."""
    cohort_set = CohortDefinitionSet()
    for index in range(size):
        rules = []
        if index % 2 == 1:
            rules.append(_rule(f"r222_{index}", 2))
        if index % 3 == 0:
            rules.append(_rule(f"r333_{index}", 3))
        if index % 11 == 0:
            rules.append(_rule(f"r444_{index}", 4))

        additional = _group(5) if index % 4 == 0 else None
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
                concept_count=len(CONDITION_CONCEPTS),
                additional=additional,
                rules=rules,
                qualified_limit=qualified_limit,
                expression_limit=expression_limit,
                end_strategy=end_strategy,
                censoring=censoring,
                censor_window=censor_window,
                collapse=collapse,
            ),
        )
    return cohort_set


def seed_cdm(conn, *, persons: int, start_year: int = 2010) -> int:
    """Seed a deterministic synthetic CDM; return the condition row count."""
    person_ids = list(range(1, persons + 1))
    conn.create_table(
        "person",
        obj=ibis.memtable(
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
        obj=ibis.memtable(
            {
                "person_id": person_ids,
                "observation_period_id": person_ids,
                "observation_period_start_date": ["2000-01-01"] * persons,
                "observation_period_end_date": ["2020-12-31"] * persons,
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
        for month, concept_id in enumerate(CONDITION_CONCEPTS, start=1):
            rows["person_id"].append(person_id)
            rows["condition_occurrence_id"].append(event_id)
            rows["condition_concept_id"].append(concept_id)
            rows["condition_start_date"].append(f"{start_year}-{month:02d}-01")
            rows["condition_end_date"].append(f"{start_year}-{month:02d}-01")
            event_id += 1

    conn.create_table("condition_occurrence", obj=ibis.memtable(rows), overwrite=True)
    return len(rows["person_id"])


def _timed_generate(cohort_set, conn, *, cohort_table: str, shared: bool) -> float:
    started = time.perf_counter()
    results = generate_cohort_set(
        cohort_set,
        backend=conn,
        cdm_schema="main",
        cohort_table=cohort_table,
        shared=shared,
    )
    elapsed = time.perf_counter() - started
    failed = [result for result in results if result.status != "COMPLETE"]
    if failed:
        raise RuntimeError(f"{len(failed)} cohort(s) failed: {failed[0].error}")
    return elapsed


def _compare(conn, left: str, right: str) -> tuple[bool, int]:
    left_rows = conn.table(left).execute()[COHORT_COLUMNS]
    right_rows = conn.table(right).execute()[COHORT_COLUMNS]
    left_rows = left_rows.sort_values(COHORT_COLUMNS).reset_index(drop=True)
    right_rows = right_rows.sort_values(COHORT_COLUMNS).reset_index(drop=True)
    return left_rows.equals(right_rows), len(left_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persons", type=int, default=20000, help="number of synthetic persons")
    parser.add_argument("--cohorts", type=int, default=64, help="number of cohort definitions")
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="run each mode N times and report the fastest run",
    )
    parser.add_argument(
        "--duckdb-path",
        default="",
        help="optional DuckDB file path (default: in-memory)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    conn = ibis.duckdb.connect(args.duckdb_path) if args.duckdb_path else ibis.duckdb.connect()
    condition_rows = seed_cdm(conn, persons=args.persons)
    cohort_set = build_family(args.cohorts)

    decomposition = decompose_cohort_set(cohort_set)
    plan, _ = build_shared_execution_plan(
        [(cohort.cohort_id, cohort.cohort_name, cohort.expression) for cohort in cohort_set]
    )

    sequential_seconds = float("inf")
    shared_seconds = float("inf")
    for attempt in range(max(1, args.repeat)):
        sequential_seconds = min(
            sequential_seconds,
            _timed_generate(
                cohort_set,
                conn,
                cohort_table=f"benchmark_sequential_{attempt}",
                shared=False,
            ),
        )
        shared_seconds = min(
            shared_seconds,
            _timed_generate(
                cohort_set,
                conn,
                cohort_table=f"benchmark_shared_{attempt}",
                shared=True,
            ),
        )

    identical, row_count = _compare(
        conn, f"benchmark_shared_{max(1, args.repeat) - 1}", f"benchmark_sequential_{max(1, args.repeat) - 1}"
    )

    decomposition_summary = decomposition.explain()
    decomposition_summary.pop("derived", None)

    report = {
        "persons": args.persons,
        "condition_rows": condition_rows,
        "cohorts": args.cohorts,
        "cohort_rows": row_count,
        "sequential_seconds": round(sequential_seconds, 3),
        "shared_seconds": round(shared_seconds, 3),
        "speedup": round(sequential_seconds / shared_seconds, 2),
        "rows_identical": identical,
        "decomposition": decomposition_summary,
        "plan": plan.explain(),
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("| metric | value |")
        print("|---|---|")
        print(f"| persons | {report['persons']:,} |")
        print(f"| condition rows | {report['condition_rows']:,} |")
        print(f"| cohort definitions | {report['cohorts']} |")
        print(f"| cohort rows | {report['cohort_rows']:,} |")
        print(f"| sequential | {report['sequential_seconds']:.3f}s |")
        print(f"| shared | {report['shared_seconds']:.3f}s |")
        print(f"| speedup | {report['speedup']}x |")
        print(f"| rows identical | {report['rows_identical']} |")
        print()
        print(
            f"decomposition: {decomposition_summary['cohorts']} cohorts -> "
            f"{len(decomposition_summary['bases'])} base(s) + "
            f"{decomposition_summary['cohorts'] - len(decomposition_summary['bases'])} derived; "
            f"definitions byte-identical="
            f"{decomposition_summary['all_definitions_byte_identical']}"
        )
        print(plan.describe())
        print(f"checkpoints: {json.dumps(plan.explain())}")

    conn.disconnect()
    return 0 if identical else 1


if __name__ == "__main__":
    raise SystemExit(main())
