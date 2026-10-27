"""Cross-dialect coverage for the HADES database support matrix.

These tests do not need a database server.  They exercise the two SQL-producing
paths against every platform HADES supports (Oracle excepted):

* ``build_cohort_query()`` -> ``render()`` -> ``translate()`` -- the SQL
  renderer used for script generation.
* ``build_cohort()`` -> ``ibis.to_sql(dialect=...)`` -- the Ibis execution
  engine's native compilation path.

Live execution is covered separately by
``tests/execution/test_database_backends.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import sqlglot

from circe.api import build_cohort_query, cohort_expression_from_json
from circe.cohortdefinition import (
    BuildExpressionQueryOptions,
    CohortExpression,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    DateOffsetStrategy,
    InclusionRule,
    PrimaryCriteria,
)
from circe.cohortdefinition.core import NumericRange
from circe.execution import build_cohort
from circe.sqlrender import render, translate
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem
from tests.execution._database_matrix import (
    HADES_PLATFORMS,
    seed_cdm,
    sqlite_supports_ibis_temporal_arithmetic,
)

COHORT_JSON = Path(__file__).with_name("cohorts") / "isolated_immune_thrombocytopenia.json"


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", sql)


@pytest.fixture(scope="module")
def rendered_tsql() -> str:
    expression = cohort_expression_from_json(COHORT_JSON.read_text())
    options = BuildExpressionQueryOptions()
    options.cdm_schema = "cdm"
    options.vocabulary_schema = "vocab"
    options.cohort_id = 1
    options.target_table = "results.cohort"
    sql = render(build_cohort_query(expression, options))
    assert "?{" not in sql, "rendered cohort SQL still contains SQLRender conditionals"
    return sql


@pytest.mark.parametrize("platform", HADES_PLATFORMS, ids=lambda platform: platform.key)
def test_rendered_cohort_sql_translates_for_platform(platform, rendered_tsql):
    translated = translate(rendered_tsql, platform.sqlrender_dialect)
    body = _strip_comments(translated)

    assert translated.strip()
    assert "results.cohort" in translated.lower()
    # Rendered SQL must not carry OHDSI parameter placeholders into a dialect.
    assert "@cdm_database_schema" not in body
    assert "@vocabulary_database_schema" not in body

    if platform.sqlglot_dialect is not None:
        statements = sqlglot.parse(translated, read=platform.sqlglot_dialect)
        assert statements
        assert all(statement is not None for statement in statements)

    # T-SQL and Redshift support ``#name`` temp tables natively.  Every other
    # target must have rewritten the names produced by the SQL builder.
    if platform.key not in {"sql_server", "synapse", "redshift"}:
        assert "CREATE TABLE #" not in body
        assert "INTO #" not in body


@pytest.fixture(scope="module")
def cohort_relation():
    ibis = pytest.importorskip("ibis")
    pytest.importorskip("duckdb")

    connection = ibis.duckdb.connect()
    seed_cdm(connection, None)
    expression = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=111))]),
            ),
            ConceptSet(
                id=2,
                expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=222))]),
            ),
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                ConditionOccurrence(
                    codeset_id=1,
                    first=True,
                    age=NumericRange(op="gte", value=18),
                )
            ]
        ),
        inclusion_rules=[
            InclusionRule(
                name="has inclusion event",
                expression=CriteriaGroup(
                    type="ALL",
                    criteria_list=[CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=2))],
                ),
            )
        ],
        end_strategy=DateOffsetStrategy(date_field="StartDate", offset=30),
    )
    relation = build_cohort(expression, backend=connection, cdm_schema="main", materialize=False)
    yield relation
    connection.disconnect()


@pytest.mark.parametrize(
    "platform",
    [platform for platform in HADES_PLATFORMS if platform.ibis_dialect is not None],
    ids=lambda platform: platform.key,
)
def test_build_cohort_compiles_for_platform(platform, cohort_relation):
    if platform.key == "sqlite" and not sqlite_supports_ibis_temporal_arithmetic():
        pytest.skip("Ibis requires SQLite >= 3.46 for date arithmetic")

    ibis = pytest.importorskip("ibis")
    sql = ibis.to_sql(cohort_relation, dialect=platform.ibis_dialect)

    assert sql.strip()
    assert "person_id" in sql
    assert "start_date" in sql

    # Verify that Ibis actually compiled for the requested dialect instead of
    # silently reusing DuckDB's quoting.
    if platform.key in {"sql_server", "synapse"}:
        assert "[" in sql
    if platform.key in {"bigquery", "spark"}:
        assert "`" in sql

    if platform.sqlglot_dialect is not None:
        sqlglot.parse_one(sql, read=platform.sqlglot_dialect)


def test_platform_matrix_matches_hades_without_oracle():
    keys = {platform.key for platform in HADES_PLATFORMS}

    assert "oracle" not in keys
    assert {
        "postgresql",
        "sql_server",
        "redshift",
        "sqlite",
        "duckdb",
        "iris",
        "snowflake",
        "spark",
        "synapse",
        "bigquery",
    } == keys


def test_every_platform_has_a_sqlrender_dialect():
    for platform in HADES_PLATFORMS:
        assert platform.sqlrender_dialect
        assert translate("SELECT 1;", platform.sqlrender_dialect)
