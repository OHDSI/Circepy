#!/usr/bin/env python
"""PostgreSQL benchmark: shared vs stand-alone cohort-set generation.

Runs against an existing OMOP CDM (it does not seed data), using a temporary
results schema.  Connection settings come from the standard ``PG*`` environment
variables:

    PGHOST (default localhost), PGPORT (5432), PGDATABASE (postgres),
    PGUSER (postgres), PGPASSWORD (required)

Example (OHDSI Lab CDM with vocabulary in ``vocab``):

    PGPASSWORD=postgres python benchmarks/decomposable_cohorts_postgres.py \
        --cdm-schema cdm --vocab-schema vocab --cohorts 32 --repeats 2

The cohort family narrows one shared entry population with inclusion rules,
additional criteria, limits, an end strategy, censoring and collapse.  Both
modes are timed alternately to reduce cache bias, and the resulting cohort
tables are compared with a two-way ``EXCEPT ALL``.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

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
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem  # noqa: E402

DEFAULT_CONCEPTS = (40481087, 4251306, 4059634, 4172829, 4309238)
PROTECTED_SCHEMAS = {"public", "cdm", "vocab", "results", "ohdsi", "webapi"}


def _concept_set(set_id: int, concept_id: int, descendants: bool = False) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(conceptId=concept_id),
                    includeDescendants=descendants,
                )
            ]
        ),
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
    concepts: tuple[int, ...],
    *,
    primary_concept_id: int | None = None,
    descendants: bool = False,
    rules: tuple[InclusionRule, ...] = (),
    additional: CriteriaGroup | None = None,
    qualified_limit: ResultLimit | None = None,
    expression_limit: ResultLimit | None = None,
    end_strategy=None,
    censoring: tuple = (),
    censor_window: Period | None = None,
    collapse: CollapseSettings | None = None,
) -> CohortExpression:
    entry_concept = concepts[0] if primary_concept_id is None else primary_concept_id
    concept_sets = [_concept_set(1, entry_concept, descendants=descendants)]
    concept_sets.extend(_concept_set(index + 2, concept_id) for index, concept_id in enumerate(concepts[1:]))

    return CohortExpression(
        concept_sets=concept_sets,
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        additional_criteria=additional,
        inclusion_rules=list(rules),
        qualified_limit=qualified_limit,
        expression_limit=expression_limit,
        end_strategy=end_strategy,
        censoring_criteria=list(censoring),
        censor_window=censor_window,
        collapse_settings=collapse,
        title="postgres benchmark",
    )


def build_family(
    size: int,
    concepts: tuple[int, ...],
    *,
    descendants: bool = False,
    distinct_primary: bool = False,
) -> CohortDefinitionSet:
    cohort_set = CohortDefinitionSet()
    for index in range(size):
        rules = []
        if index % 2 == 1 and len(concepts) > 1:
            rules.append(_rule(f"r2_{index}", 2))
        if index % 3 == 0 and len(concepts) > 2:
            rules.append(_rule(f"r3_{index}", 3))
        additional = _group(4) if index % 4 == 0 and len(concepts) > 3 else None
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
        censoring = [ConditionOccurrence(codeset_id=2)] if index % 9 == 0 and len(concepts) > 1 else []
        censor_window = Period(start_date="2010-01-01", end_date="2020-12-31") if censoring else None
        collapse = CollapseSettings(era_pad=index % 3) if index % 10 == 0 else None

        cohort_set.add(
            cohort_id=index + 1,
            cohort_name=f"cohort {index}",
            expression=_expression(
                concepts,
                primary_concept_id=(concepts[index % len(concepts)] if distinct_primary else concepts[0]),
                descendants=descendants,
                rules=tuple(rules),
                additional=additional,
                qualified_limit=qualified_limit,
                expression_limit=expression_limit,
                end_strategy=end_strategy,
                censoring=tuple(censoring),
                censor_window=censor_window,
                collapse=collapse,
            ),
        )
    return cohort_set


def _connect():
    try:
        import psycopg  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "psycopg is required for the PostgreSQL benchmark: pip install 'psycopg[binary]'"
        ) from exc

    password = os.environ.get("PGPASSWORD")
    if not password:
        raise SystemExit("PGPASSWORD is required (PGHOST/PGPORT/PGDATABASE/PGUSER are optional).")

    return ibis.postgres.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", "5432")),
        database=os.environ.get("PGDATABASE", "postgres"),
        user=os.environ.get("PGUSER", "postgres"),
        password=password,
    )


def _generate(cohort_set, conn, *, schema: str, table: str, shared: bool, args) -> float:
    started = time.perf_counter()
    results = generate_cohort_set(
        cohort_set,
        backend=conn,
        cdm_schema=args.cdm_schema,
        vocabulary_schema=args.vocab_schema,
        results_schema=schema,
        cohort_table=table,
        shared=shared,
    )
    elapsed = time.perf_counter() - started
    failed = [result for result in results if result.status != "COMPLETE"]
    if failed:
        raise RuntimeError(f"cohorts failed: {[(r.cohort_id, r.error) for r in failed]}")
    return elapsed


def _symmetric_difference(conn, schema: str, left: str, right: str) -> int:
    columns = "cohort_definition_id, subject_id, cohort_start_date, cohort_end_date"
    query = f"""
    select count(*) from (
      (select {columns} from "{schema}".{left} except all select {columns} from "{schema}".{right})
      union all
      (select {columns} from "{schema}".{right} except all select {columns} from "{schema}".{left})
    ) diff
    """
    return int(conn.raw_sql(query).fetchone()[0])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohorts", type=int, default=12)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--cdm-schema", default="cdm")
    parser.add_argument("--vocab-schema", default="vocab")
    parser.add_argument(
        "--results-schema",
        default="circe_bench",
        help="temporary schema owned by this script (created and dropped)",
    )
    parser.add_argument(
        "--concepts",
        default=",".join(str(value) for value in DEFAULT_CONCEPTS),
        help="comma-separated concept ids: entry, rules, additional criteria",
    )
    parser.add_argument("--descendants", action="store_true")
    parser.add_argument("--distinct-primary", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.results_schema in PROTECTED_SCHEMAS or not args.results_schema.startswith("circe_"):
        raise SystemExit(
            f"refusing to create/drop results schema {args.results_schema!r}; "
            "use a name starting with 'circe_'"
        )

    concepts = tuple(int(value) for value in args.concepts.split(",") if value.strip())
    if not concepts:
        raise SystemExit("--concepts must contain at least one concept id")

    conn = _connect()
    conn.raw_sql(f'drop schema if exists "{args.results_schema}" cascade')
    conn.raw_sql(f'create schema "{args.results_schema}"')

    cohort_set = build_family(
        args.cohorts,
        concepts,
        descendants=args.descendants,
        distinct_primary=args.distinct_primary,
    )

    # Warm the CDM/vocabulary cache before timing.
    warm = CohortDefinitionSet()
    warm.add(
        cohort_id=0,
        cohort_name="warmup",
        expression=_expression(concepts, descendants=args.descendants),
    )
    _generate(warm, conn, schema=args.results_schema, table="warmup", shared=False, args=args)

    timings: dict[str, list[float]] = {"sequential": [], "shared": []}
    for repeat in range(args.repeats):
        order = [("sequential", False), ("shared", True)]
        if repeat % 2:
            order.reverse()
        for label, shared in order:
            timings[label].append(
                _generate(
                    cohort_set,
                    conn,
                    schema=args.results_schema,
                    table=f"cohort_{label}_{repeat}",
                    shared=shared,
                    args=args,
                )
            )

    last_sequential = f"cohort_sequential_{args.repeats - 1}"
    last_shared = f"cohort_shared_{args.repeats - 1}"
    difference = _symmetric_difference(conn, args.results_schema, last_sequential, last_shared)
    rows = int(conn.raw_sql(f'select count(*) from "{args.results_schema}".{last_shared}').fetchone()[0])

    sequential_median = statistics.median(timings["sequential"])
    shared_median = statistics.median(timings["shared"])
    report = {
        "cohorts": args.cohorts,
        "descendants": args.descendants,
        "distinct_primary": args.distinct_primary,
        "cohort_rows": rows,
        "sequential_seconds": [round(value, 2) for value in timings["sequential"]],
        "shared_seconds": [round(value, 2) for value in timings["shared"]],
        "sequential_median": round(sequential_median, 2),
        "shared_median": round(shared_median, 2),
        "speedup_median": round(sequential_median / shared_median, 2),
        "speedup_best": round(min(timings["sequential"]) / min(timings["shared"]), 2),
        "symmetric_difference_rows": difference,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("| metric | value |")
        print("|---|---|")
        for key, value in report.items():
            print(f"| {key} | {value} |")

    conn.raw_sql(f'drop schema if exists "{args.results_schema}" cascade')
    conn.disconnect()
    return 0 if difference == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
