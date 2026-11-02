"""Parity checks between the ibis engine and the Java-equivalent SQL builder.

These tests run the same CohortExpression through both paths on a synthetic
DuckDB CDM and compare the resulting cohort rows. They target the specific
semantic edges raised in review (censoring bounds, era-collapse tie-breaking,
observation-period duplication, death/specimen end dates).
"""

from __future__ import annotations

from circe.api import build_cohort
from circe.cohortdefinition import (
    BuildExpressionQueryOptions,
    CohortExpression,
    CohortExpressionQueryBuilder,
    ConditionOccurrence,
    Death,
    Observation,
    PrimaryCriteria,
    Specimen,
)
from circe.cohortdefinition.core import (
    CollapseSettings,
    DateOffsetStrategy,
    ObservationFilter,
    ResultLimit,
)
from circe.sqlrender import render, split_sql, translate
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def _create_table(conn, name: str, schema: dict[str, str], rows: list[dict]) -> None:
    import datetime

    import ibis

    for column, dtype in schema.items():
        if dtype == "date":
            for row in rows:
                if row.get(column) is not None:
                    row[column] = datetime.date.fromisoformat(row[column])
    data = {column: [row[column] for row in rows] for column in schema}
    conn.create_table(name, obj=ibis.memtable(data, schema=ibis.schema(schema)), overwrite=True)


def _rows(result) -> set[tuple[int, str, str]]:
    rows = result.to_pyarrow().to_pylist()
    if not rows:
        return set()
    subject_col = "subject_id" if "subject_id" in rows[0] else "person_id"
    start_col = "cohort_start_date" if "cohort_start_date" in rows[0] else "start_date"
    end_col = "cohort_end_date" if "cohort_end_date" in rows[0] else "end_date"
    return {(int(row[subject_col]), str(row[start_col])[:10], str(row[end_col])[:10]) for row in rows}


def _legacy_rows(conn, expression: CohortExpression, *, cohort_id: int = 999) -> set[tuple[int, str, str]]:
    opts = BuildExpressionQueryOptions()
    opts.cohort_id_field_name = "cohort_definition_id"
    opts.cohort_id = cohort_id
    opts.cdm_schema = "main"
    opts.vocabulary_schema = "main"
    opts.result_schema = "main"
    opts.target_table = "legacy"
    opts.generate_stats = False

    sql = CohortExpressionQueryBuilder().build_expression_query(expression, opts)
    rendered = render(
        sql,
        cdm_database_schema="main",
        vocabulary_database_schema="main",
        results_database_schema="main",
        target_database_schema="main",
        target_cohort_table="legacy",
        target_cohort_id=cohort_id,
    )
    translated = translate(rendered, target_dialect="duckdb")
    conn.drop_table("legacy", force=True)
    conn.raw_sql(
        "CREATE TABLE legacy (cohort_definition_id BIGINT, subject_id BIGINT, "
        "cohort_start_date DATE, cohort_end_date DATE)"
    )
    for statement in split_sql(translated):
        statement = statement.strip()
        if statement:
            conn.raw_sql(statement)
    return _rows(conn.table("legacy").filter(lambda t: t.cohort_definition_id == cohort_id))


def _base_tables(conn):
    _create_table(
        conn,
        "person",
        {"person_id": "int64", "year_of_birth": "int64", "gender_concept_id": "int64"},
        [{"person_id": 1, "year_of_birth": 1980, "gender_concept_id": 8507}],
    )
    _create_table(
        conn,
        "observation_period",
        {
            "person_id": "int64",
            "observation_period_id": "int64",
            "observation_period_start_date": "date",
            "observation_period_end_date": "date",
        },
        [
            {
                "person_id": 1,
                "observation_period_id": 1,
                "observation_period_start_date": "2019-01-01",
                "observation_period_end_date": "2021-12-31",
            }
        ],
    )
    _create_table(
        conn,
        "concept",
        {"concept_id": "int64", "concept_name": "string"},
        [{"concept_id": 111, "concept_name": "condition"}, {"concept_id": 222, "concept_name": "censor"}],
    )


def test_censoring_bound_uses_cohort_end_not_observation_end():
    import ibis

    conn = ibis.duckdb.connect()
    _base_tables(conn)
    _create_table(
        conn,
        "condition_occurrence",
        {
            "person_id": "int64",
            "condition_occurrence_id": "int64",
            "condition_concept_id": "int64",
            "condition_start_date": "date",
            "condition_end_date": "date",
            "visit_occurrence_id": "int64",
        },
        [
            {
                "person_id": 1,
                "condition_occurrence_id": 10,
                "condition_concept_id": 111,
                "condition_start_date": "2020-01-01",
                "condition_end_date": "2020-01-01",
                "visit_occurrence_id": 0,
            }
        ],
    )
    _create_table(
        conn,
        "observation",
        {
            "person_id": "int64",
            "observation_id": "int64",
            "observation_concept_id": "int64",
            "observation_date": "date",
            "observation_type_concept_id": "int64",
            "value_as_number": "float64",
            "value_as_string": "string",
            "value_as_concept_id": "int64",
            "qualifier_concept_id": "int64",
            "unit_concept_id": "int64",
            "provider_id": "int64",
            "visit_occurrence_id": "int64",
            "observation_source_value": "string",
            "observation_source_concept_id": "int64",
            "qualifier_source_value": "string",
        },
        [
            {
                "person_id": 1,
                "observation_id": 20,
                "observation_concept_id": 222,
                "observation_date": "2020-02-01",
                "observation_type_concept_id": 0,
                "value_as_number": None,
                "value_as_string": None,
                "value_as_concept_id": 0,
                "qualifier_concept_id": 0,
                "unit_concept_id": 0,
                "provider_id": 0,
                "visit_occurrence_id": 0,
                "observation_source_value": None,
                "observation_source_concept_id": 0,
                "qualifier_source_value": None,
            }
        ],
    )

    expression = CohortExpression(
        concept_sets=[_concept_set(1, 111), _concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
            observation_window=ObservationFilter(prior_days=0, post_days=0),
            primary_limit=ResultLimit(type="All"),
        ),
        end_strategy=DateOffsetStrategy(offset=10, date_field="EndDate"),
        censoring_criteria=[Observation(codeset_id=2)],
        collapse_settings=CollapseSettings(collapse_type="ERA", era_pad=0),
        expression_limit=ResultLimit(type="All"),
    )

    ibis_rows = _rows(build_cohort(expression, backend=conn, cdm_schema="main"))
    legacy_rows = _legacy_rows(conn, expression)
    assert ibis_rows == legacy_rows, f"ibis={ibis_rows} legacy={legacy_rows}"


def _assert_parity(conn, expression: CohortExpression):
    ibis_rows = _rows(build_cohort(expression, backend=conn, cdm_schema="main"))
    legacy_rows = _legacy_rows(conn, expression)
    assert ibis_rows == legacy_rows, f"ibis={ibis_rows} legacy={legacy_rows}"


def test_death_end_date_matches_java():
    import ibis

    conn = ibis.duckdb.connect()
    _base_tables(conn)
    _create_table(
        conn,
        "death",
        {
            "person_id": "int64",
            "death_date": "date",
            "death_type_concept_id": "int64",
            "cause_concept_id": "int64",
            "cause_source_concept_id": "int64",
        },
        [
            {
                "person_id": 1,
                "death_date": "2020-03-01",
                "death_type_concept_id": 0,
                "cause_concept_id": 111,
                "cause_source_concept_id": 0,
            }
        ],
    )
    expression = CohortExpression(
        concept_sets=[_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[Death(codeset_id=1)],
            observation_window=ObservationFilter(prior_days=0, post_days=0),
            primary_limit=ResultLimit(type="All"),
        ),
        collapse_settings=CollapseSettings(collapse_type="ERA", era_pad=0),
        expression_limit=ResultLimit(type="All"),
    )
    _assert_parity(conn, expression)


def test_specimen_end_date_matches_java():
    import ibis

    conn = ibis.duckdb.connect()
    _base_tables(conn)
    _create_table(
        conn,
        "specimen",
        {
            "person_id": "int64",
            "specimen_id": "int64",
            "specimen_concept_id": "int64",
            "specimen_date": "date",
            "visit_occurrence_id": "int64",
            "quantity": "float64",
            "unit_concept_id": "int64",
            "anatomic_site_concept_id": "int64",
            "disease_status_concept_id": "int64",
            "specimen_source_id": "string",
            "specimen_source_concept_id": "int64",
        },
        [
            {
                "person_id": 1,
                "specimen_id": 5,
                "specimen_concept_id": 111,
                "specimen_date": "2020-03-01",
                "visit_occurrence_id": 0,
                "quantity": None,
                "unit_concept_id": 0,
                "anatomic_site_concept_id": 0,
                "disease_status_concept_id": 0,
                "specimen_source_id": None,
                "specimen_source_concept_id": 0,
            }
        ],
    )
    expression = CohortExpression(
        concept_sets=[_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[Specimen(codeset_id=1)],
            observation_window=ObservationFilter(prior_days=0, post_days=0),
            primary_limit=ResultLimit(type="All"),
        ),
        collapse_settings=CollapseSettings(collapse_type="ERA", era_pad=0),
        expression_limit=ResultLimit(type="All"),
    )
    _assert_parity(conn, expression)


def test_overlapping_observation_periods_match_java():
    import ibis

    conn = ibis.duckdb.connect()
    _create_table(
        conn,
        "person",
        {"person_id": "int64", "year_of_birth": "int64", "gender_concept_id": "int64"},
        [{"person_id": 1, "year_of_birth": 1980, "gender_concept_id": 8507}],
    )
    _create_table(
        conn,
        "observation_period",
        {
            "person_id": "int64",
            "observation_period_id": "int64",
            "observation_period_start_date": "date",
            "observation_period_end_date": "date",
        },
        [
            {
                "person_id": 1,
                "observation_period_id": 1,
                "observation_period_start_date": "2019-01-01",
                "observation_period_end_date": "2020-04-15",
            },
            {
                "person_id": 1,
                "observation_period_id": 2,
                "observation_period_start_date": "2020-01-01",
                "observation_period_end_date": "2021-12-31",
            },
        ],
    )
    _create_table(
        conn,
        "concept",
        {"concept_id": "int64", "concept_name": "string"},
        [{"concept_id": 111, "concept_name": "condition"}],
    )
    _create_table(
        conn,
        "condition_occurrence",
        {
            "person_id": "int64",
            "condition_occurrence_id": "int64",
            "condition_concept_id": "int64",
            "condition_start_date": "date",
            "condition_end_date": "date",
            "visit_occurrence_id": "int64",
        },
        [
            {
                "person_id": 1,
                "condition_occurrence_id": 10,
                "condition_concept_id": 111,
                "condition_start_date": "2020-03-01",
                "condition_end_date": "2020-03-25",
                "visit_occurrence_id": 0,
            }
        ],
    )
    expression = CohortExpression(
        concept_sets=[_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
            observation_window=ObservationFilter(prior_days=0, post_days=0),
            primary_limit=ResultLimit(type="All"),
        ),
        end_strategy=DateOffsetStrategy(offset=30, date_field="EndDate"),
        collapse_settings=CollapseSettings(collapse_type="ERA", era_pad=0),
        expression_limit=ResultLimit(type="All"),
    )
    _assert_parity(conn, expression)


def test_era_collapse_same_start_different_end_matches_java():
    import ibis

    conn = ibis.duckdb.connect()
    _base_tables(conn)
    _create_table(
        conn,
        "condition_occurrence",
        {
            "person_id": "int64",
            "condition_occurrence_id": "int64",
            "condition_concept_id": "int64",
            "condition_start_date": "date",
            "condition_end_date": "date",
            "visit_occurrence_id": "int64",
        },
        [
            {
                "person_id": 1,
                "condition_occurrence_id": 1,
                "condition_concept_id": 111,
                "condition_start_date": "2020-01-01",
                "condition_end_date": "2020-01-05",
                "visit_occurrence_id": 0,
            },
            {
                "person_id": 1,
                "condition_occurrence_id": 2,
                "condition_concept_id": 111,
                "condition_start_date": "2020-01-01",
                "condition_end_date": "2020-01-10",
                "visit_occurrence_id": 0,
            },
        ],
    )
    expression = CohortExpression(
        concept_sets=[_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
            observation_window=ObservationFilter(prior_days=0, post_days=0),
            primary_limit=ResultLimit(type="All"),
        ),
        end_strategy=DateOffsetStrategy(offset=0, date_field="EndDate"),
        collapse_settings=CollapseSettings(collapse_type="ERA", era_pad=0),
        expression_limit=ResultLimit(type="All"),
    )
    _assert_parity(conn, expression)
