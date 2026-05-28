"""Equivalence tests: string-template + SqlRender vs sqlglot builders.

For each criteria scenario, we build SQL via both paths, execute both
in DuckDB, and assert the result row sets are identical.
"""

import datetime
from typing import Any

import pytest

from circe.cohortdefinition import (
    ConditionOccurrence,
    DateAdjustment,
    DrugExposure,
    NumericRange,
    VisitOccurrence,
)
from circe.cohortdefinition.builders.condition_occurrence import (
    ConditionOccurrenceSqlBuilder,
)
from circe.cohortdefinition.builders.drug_exposure import DrugExposureSqlBuilder
from circe.cohortdefinition.builders.visit_occurrence import (
    VisitOccurrenceSqlBuilder,
)
from circe.cohortdefinition.sqlglot_builders import (
    ConditionOccurrenceGlotBuilder,
    DrugExposureGlotBuilder,
    VisitOccurrenceGlotBuilder,
)
from tests.test_utils_db import DuckDBTestHelper


@pytest.fixture(scope="module")
def db():
    helper = DuckDBTestHelper()
    _create_test_schema(helper)
    return helper


def _create_test_schema(helper: DuckDBTestHelper):
    con = helper.con

    con.execute("DROP TABLE IF EXISTS person")
    con.execute("""
        CREATE TABLE person (
            person_id INTEGER,
            year_of_birth INTEGER,
            gender_concept_id INTEGER,
            race_concept_id INTEGER,
            ethnicity_concept_id INTEGER
        )
    """)
    con.execute("INSERT INTO person VALUES (1, 1980, 8507, 0, 0)")
    con.execute("INSERT INTO person VALUES (2, 1990, 8532, 0, 0)")
    con.execute("INSERT INTO person VALUES (3, 1970, 8507, 0, 0)")
    con.execute("INSERT INTO person VALUES (4, 2000, 8532, 0, 0)")

    con.execute("DROP TABLE IF EXISTS condition_occurrence")
    con.execute("""
        CREATE TABLE condition_occurrence (
            person_id INTEGER,
            condition_occurrence_id INTEGER,
            condition_concept_id INTEGER,
            condition_start_date DATE,
            condition_end_date DATE,
            condition_type_concept_id INTEGER,
            stop_reason VARCHAR,
            condition_status_concept_id INTEGER,
            visit_occurrence_id INTEGER,
            provider_id INTEGER,
            condition_source_concept_id INTEGER
        )
    """)
    con.execute(
        "INSERT INTO condition_occurrence VALUES (1, 101, 10, '2020-01-15', '2020-01-20', 100, NULL, 0, 1, NULL, NULL)"
    )
    con.execute(
        "INSERT INTO condition_occurrence VALUES (1, 102, 11, '2020-02-01', '2020-02-05', 200, 'resolved', 0, 1, NULL, NULL)"
    )
    con.execute(
        "INSERT INTO condition_occurrence VALUES (2, 103, 10, '2020-03-01', '2020-03-10', 100, NULL, 0, 2, NULL, NULL)"
    )
    con.execute(
        "INSERT INTO condition_occurrence VALUES (3, 104, 10, '2020-01-01', '2020-01-10', 100, NULL, 0, NULL, NULL, NULL)"
    )
    con.execute(
        "INSERT INTO condition_occurrence VALUES (4, 105, 99, '2020-06-01', '2020-06-05', 300, NULL, 0, NULL, NULL, NULL)"
    )

    con.execute("DROP TABLE IF EXISTS drug_exposure")
    con.execute("""
        CREATE TABLE drug_exposure (
            person_id INTEGER,
            drug_exposure_id INTEGER,
            drug_concept_id INTEGER,
            drug_exposure_start_date DATE,
            drug_exposure_end_date DATE,
            drug_type_concept_id INTEGER,
            stop_reason VARCHAR,
            refills INTEGER,
            quantity NUMERIC,
            days_supply INTEGER,
            route_concept_id INTEGER,
            dose_unit_concept_id INTEGER,
            provider_id INTEGER,
            visit_occurrence_id INTEGER,
            drug_source_concept_id INTEGER,
            lot_number VARCHAR
        )
    """)
    con.execute(
        "INSERT INTO drug_exposure VALUES (1, 201, 20, '2020-01-10', '2020-01-20', 50, NULL, 2, 10, 10, NULL, NULL, NULL, 1, NULL, NULL)"
    )
    con.execute(
        "INSERT INTO drug_exposure VALUES (1, 202, 21, '2020-02-15', '2020-02-25', 60, 'stopped', 0, 5, 10, NULL, NULL, NULL, 1, NULL, 'ABC123')"
    )
    con.execute(
        "INSERT INTO drug_exposure VALUES (2, 203, 20, '2020-03-05', '2020-03-15', 50, NULL, 1, 20, 10, NULL, NULL, NULL, 2, NULL, NULL)"
    )
    con.execute(
        "INSERT INTO drug_exposure VALUES (3, 204, 20, '2020-01-05', '2020-01-15', 50, NULL, 0, 15, 5, NULL, NULL, NULL, NULL, NULL, NULL)"
    )
    con.execute(
        "INSERT INTO drug_exposure VALUES (4, 205, 99, '2020-07-01', '2020-07-10', 70, NULL, 0, 5, 30, NULL, NULL, NULL, NULL, NULL, NULL)"
    )

    con.execute("DROP TABLE IF EXISTS visit_occurrence")
    con.execute("""
        CREATE TABLE visit_occurrence (
            person_id INTEGER,
            visit_occurrence_id INTEGER,
            visit_concept_id INTEGER,
            visit_start_date DATE,
            visit_end_date DATE,
            visit_type_concept_id INTEGER,
            provider_id INTEGER,
            care_site_id INTEGER,
            visit_source_concept_id INTEGER
        )
    """)
    con.execute(
        "INSERT INTO visit_occurrence VALUES (1, 1, 30, '2020-01-10', '2020-01-20', 500, NULL, NULL, NULL)"
    )
    con.execute(
        "INSERT INTO visit_occurrence VALUES (2, 2, 30, '2020-03-01', '2020-03-15', 500, NULL, NULL, NULL)"
    )
    con.execute(
        "INSERT INTO visit_occurrence VALUES (3, 3, 31, '2020-01-01', '2020-01-10', 600, NULL, NULL, NULL)"
    )
    con.execute(
        "INSERT INTO visit_occurrence VALUES (4, 4, 99, '2020-06-01', '2020-06-10', 700, NULL, NULL, NULL)"
    )

    con.execute("DROP TABLE IF EXISTS observation_period")
    con.execute("""
        CREATE TABLE observation_period (
            person_id INTEGER,
            observation_period_start_date DATE,
            observation_period_end_date DATE
        )
    """)
    for pid in range(1, 5):
        con.execute(f"INSERT INTO observation_period VALUES ({pid}, '2019-01-01', '2021-12-31')")

    con.execute("DELETE FROM Codesets")
    for codeset_id, concept_id in [(1, 10), (2, 20), (3, 30), (4, 99)]:
        con.execute(f"INSERT INTO Codesets (codeset_id, concept_id) VALUES ({codeset_id}, {concept_id})")

    con.execute("DROP TABLE IF EXISTS provider")
    con.execute("""
        CREATE TABLE provider (
            provider_id INTEGER,
            specialty_concept_id INTEGER
        )
    """)

    con.execute("DROP TABLE IF EXISTS care_site")
    con.execute("""
        CREATE TABLE care_site (
            care_site_id INTEGER,
            place_of_service_concept_id INTEGER
        )
    """)


def _sql_param_replace(sql: str) -> str:
    return sql.replace("@cdm_database_schema.", "main.")


def _glot_to_duckdb(sql: str) -> str:
    return sql.replace("#Codesets", "Codesets").replace("#", "")


def _run_glot(db: DuckDBTestHelper, select) -> list[Any]:
    sql = select.sql(dialect="duckdb")
    sql = _glot_to_duckdb(sql)
    return _normalize_dates(db.execute_raw(f"SELECT * FROM ({sql}) C").fetchall())


def _result_set(results: list[Any]) -> set[tuple]:
    return {tuple(r) for r in results}


def _normalize_dates(results: list[Any]) -> list[list]:
    out = []
    for row in results:
        r = list(row)
        for i, val in enumerate(r):
            if isinstance(val, datetime.datetime):
                r[i] = val.date()
        out.append(r)
    return out


class TestConditionOccurrenceEquivalence:
    builder = ConditionOccurrenceSqlBuilder()
    glot = ConditionOccurrenceGlotBuilder()

    def test_simple_codeset_match(self, db: DuckDBTestHelper):
        co = ConditionOccurrence(codeset_id=1)

        tsql = self.builder.get_criteria_sql(co)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(co)))

        assert rows_a == rows_b, "Simple codeset match: rows differ"

    def test_date_range_filter(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import DateRange

        co = ConditionOccurrence(
            codeset_id=1,
            occurrence_start_date=DateRange(op="gte", value="2020-02-01"),
        )

        tsql = self.builder.get_criteria_sql(co)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(co)))

        assert rows_a == rows_b, "Date range filter: rows differ"

    def test_age_filter(self, db: DuckDBTestHelper):
        co = ConditionOccurrence(
            codeset_id=1,
            age=NumericRange(op="gte", value=40),
        )

        tsql = self.builder.get_criteria_sql(co)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(co)))

        assert rows_a == rows_b, "Age filter: rows differ"

    def test_first_occurrence(self, db: DuckDBTestHelper):
        co = ConditionOccurrence(codeset_id=1, first=True)

        tsql = self.builder.get_criteria_sql(co)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(co)))

        assert rows_a == rows_b, "First occurrence: rows differ"

    def test_date_adjustment(self, db: DuckDBTestHelper):
        co = ConditionOccurrence(
            codeset_id=1,
            date_adjustment=DateAdjustment(start_offset=3, end_offset=0),
        )

        tsql = self.builder.get_criteria_sql(co)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(co)))

        assert rows_a == rows_b, "Date adjustment: rows differ"

    def test_date_adjustment_dates(self, db: DuckDBTestHelper):
        """Verify adjusted date values specifically."""
        co = ConditionOccurrence(
            codeset_id=1,
            date_adjustment=DateAdjustment(start_offset=2, end_offset=1),
        )

        tsql = self.builder.get_criteria_sql(co)
        rows_a = db.query(f"SELECT C.start_date, C.end_date FROM ({_sql_param_replace(tsql)}) C")
        row_a = rows_a[0] if rows_a else None

        glot_select = self.glot.build_select(co)
        glot_sql = glot_select.sql(dialect="duckdb")
        glot_sql = _glot_to_duckdb(glot_sql)
        rows_b = db.execute_raw(f"SELECT C.start_date, C.end_date FROM ({glot_sql}) C").fetchall()
        row_b = rows_b[0] if rows_b else None

        def _to_dates(r):
            if r is None:
                return None
            r = list(r)
            for i in range(2):
                if isinstance(r[i], datetime.datetime):
                    r[i] = r[i].date()
            return tuple(r)

        row_a, row_b = _to_dates(row_a), _to_dates(row_b)
        assert row_a == row_b, f"Date adjustment values differ: {row_a} vs {row_b}"


class TestDrugExposureEquivalence:
    builder = DrugExposureSqlBuilder()
    glot = DrugExposureGlotBuilder()

    def test_simple_codeset_match(self, db: DuckDBTestHelper):
        de = DrugExposure(codeset_id=2)

        tsql = self.builder.get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(de)))

        assert rows_a == rows_b, "Drug simple codeset match: rows differ"

    def test_days_supply_filter(self, db: DuckDBTestHelper):
        de = DrugExposure(codeset_id=2, days_supply=NumericRange(op="gte", value=8))

        tsql = self.builder.get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(de)))

        assert rows_a == rows_b, "Drug days_supply filter: rows differ"

    def test_first_drug_exposure(self, db: DuckDBTestHelper):
        de = DrugExposure(codeset_id=2, first=True)

        tsql = self.builder.get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(de)))

        assert rows_a == rows_b, "Drug first: rows differ"

    def test_drug_type_exclude(self, db: DuckDBTestHelper):
        from circe.vocabulary.concept import Concept

        de = DrugExposure(
            codeset_id=2,
            drug_type=[Concept(concept_id=70)],
            drug_type_exclude=True,
        )

        tsql = self.builder.get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(de)))

        assert rows_a == rows_b, "Drug type exclude: rows differ"


class TestVisitOccurrenceEquivalence:
    builder = VisitOccurrenceSqlBuilder()
    glot = VisitOccurrenceGlotBuilder()

    def test_simple_codeset_match(self, db: DuckDBTestHelper):
        vo = VisitOccurrence(codeset_id=3)

        tsql = self.builder.get_criteria_sql(vo)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(vo)))

        assert rows_a == rows_b, "Visit simple codeset match: rows differ"

    def test_visit_length_filter(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import NumericRange

        vo = VisitOccurrence(
            codeset_id=3,
            visit_length=NumericRange(op="gt", value=10),
        )

        tsql = self.builder.get_criteria_sql(vo)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(vo)))

        assert rows_a == rows_b, "Visit length filter: rows differ"

    def test_first_visit(self, db: DuckDBTestHelper):
        vo = VisitOccurrence(codeset_id=3, first=True)

        tsql = self.builder.get_criteria_sql(vo)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))

        rows_b = _result_set(_run_glot(db, self.glot.build_select(vo)))

        assert rows_a == rows_b, "Visit first: rows differ"


class TestCrossCriteriaEquivalence:
    """Key test: all three criteria types return same populations."""

    def test_condition_and_drug_and_visit_all_match(self, db: DuckDBTestHelper):
        """Each criteria type should find overlapping patients."""
        co = ConditionOccurrence(codeset_id=1)
        de = DrugExposure(codeset_id=2)
        vo = VisitOccurrence(codeset_id=3)

        def _get_person_ids(builder, criteria) -> set:
            sql = _glot_to_duckdb(builder.build_select(criteria).sql(dialect="duckdb"))
            return {r[0] for r in db.execute_raw(f"SELECT * FROM ({sql}) C").fetchall()}

        co_rows = _get_person_ids(ConditionOccurrenceGlotBuilder(), co)
        de_rows = _get_person_ids(DrugExposureGlotBuilder(), de)
        vo_rows = _get_person_ids(VisitOccurrenceGlotBuilder(), vo)

        assert co_rows == {1, 2, 3}, f"CO should find persons 1,2,3, got {co_rows}"
        assert de_rows == {1, 2, 3}, f"DE should find persons 1,2,3, got {de_rows}"
        assert vo_rows == {1, 2}, (
            f"VO should find persons 1,2 (patient 3 has concept 31 not 30), got {vo_rows}"
        )

    def test_rejects_non_matching(self, db: DuckDBTestHelper):
        """Person 4 should NOT be returned by any criteria since concept 99 doesn't match codesets 1,2,3."""
        co = ConditionOccurrence(codeset_id=1)
        de = DrugExposure(codeset_id=2)
        vo = VisitOccurrence(codeset_id=3)

        for builder, label, criteria in [
            (ConditionOccurrenceGlotBuilder(), "CO", co),
            (DrugExposureGlotBuilder(), "DE", de),
            (VisitOccurrenceGlotBuilder(), "VO", vo),
        ]:
            sql = _glot_to_duckdb(builder.build_select(criteria).sql(dialect="duckdb"))
            rows = {r[0] for r in db.execute_raw(f"SELECT * FROM ({sql}) C").fetchall()}
            assert 4 not in rows, f"{label} should not return person 4"

    def test_all_paths_produce_same_row_count(self, db: DuckDBTestHelper):
        """String-template and sqlglot paths produce same number of rows for each criteria."""
        scenarios = [
            (
                ConditionOccurrence(codeset_id=1),
                ConditionOccurrenceSqlBuilder(),
                ConditionOccurrenceGlotBuilder(),
            ),
            (DrugExposure(codeset_id=2), DrugExposureSqlBuilder(), DrugExposureGlotBuilder()),
            (VisitOccurrence(codeset_id=3), VisitOccurrenceSqlBuilder(), VisitOccurrenceGlotBuilder()),
        ]

        for criteria, str_builder, glot_builder in scenarios:
            tsql = str_builder.get_criteria_sql(criteria)
            rows_a = _normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C"))

            rows_b = _run_glot(db, glot_builder.build_select(criteria))

            assert len(rows_a) == len(rows_b), (
                f"{type(criteria).__name__}: row count mismatch: string={len(rows_a)}, glot={len(rows_b)}"
            )


class TestComprehensiveConditionOccurrence:
    """Exercise all optional CO fields including source concept, condition status/type CS, provider, visit type."""

    def test_with_source_concept(self, db: DuckDBTestHelper):
        db.con.execute("DELETE FROM Codesets")
        for codeset_id, concept_id in [(1, 10), (12, 11)]:
            db.con.execute(
                f"INSERT INTO Codesets (codeset_id, concept_id) VALUES ({codeset_id}, {concept_id})"
            )

        co = ConditionOccurrence(
            codeset_id=1,
            condition_source_concept=12,
        )
        tsql = ConditionOccurrenceSqlBuilder().get_criteria_sql(co)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, ConditionOccurrenceGlotBuilder().build_select(co)))
        assert rows_a == rows_b, "CO with source concept: rows differ"

    def test_with_provider_and_visit(self, db: DuckDBTestHelper):
        db.con.execute("INSERT INTO provider VALUES (1, 100)")
        db.con.execute(
            "INSERT INTO visit_occurrence VALUES (5, 5, 30, '2020-05-01', '2020-05-05', 500, 1, NULL, NULL)"
        )
        db.con.execute(
            "INSERT INTO condition_occurrence VALUES (5, 106, 10, '2020-05-02', '2020-05-04', 100, NULL, 0, 5, 1, NULL)"
        )
        db.con.execute("INSERT INTO observation_period VALUES (5, '2019-01-01', '2021-12-31')")

        from circe.cohortdefinition import ConceptSetSelection

        co = ConditionOccurrence(
            codeset_id=1,
            provider_specialty_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            visit_type_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
        )
        tsql = ConditionOccurrenceSqlBuilder().get_criteria_sql(co)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, ConditionOccurrenceGlotBuilder().build_select(co)))
        assert rows_a == rows_b, "CO with provider and visit CS: rows differ"

    def test_with_condition_status(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import ConceptSetSelection

        db.con.execute("UPDATE condition_occurrence SET condition_status_concept_id=555 WHERE person_id=1")
        db.con.execute("DELETE FROM Codesets")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (1, 10)")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (5, 555)")

        co = ConditionOccurrence(
            codeset_id=1,
            condition_status_cs=ConceptSetSelection(codeset_id=5, is_exclusion=False),
        )
        tsql = ConditionOccurrenceSqlBuilder().get_criteria_sql(co)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, ConditionOccurrenceGlotBuilder().build_select(co)))
        assert rows_a == rows_b, "CO with condition status CS: rows differ"

    def test_with_condition_type_cs(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import ConceptSetSelection

        db.con.execute("DELETE FROM Codesets")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (1, 10)")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (5, 200)")

        co = ConditionOccurrence(
            codeset_id=1,
            condition_type_cs=ConceptSetSelection(codeset_id=5, is_exclusion=False),
        )
        tsql = ConditionOccurrenceSqlBuilder().get_criteria_sql(co)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, ConditionOccurrenceGlotBuilder().build_select(co)))
        assert rows_a == rows_b, "CO with condition type CS: rows differ"


class TestComprehensiveDrugExposure:
    """Exercise all optional DE fields: route, dose, lot, refills, quantity, days_supply, stop_reason, date adjustment."""

    def test_with_route_dose_lot(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import ConceptSetSelection

        db.con.execute("DELETE FROM Codesets")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (2, 20)")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (7, 777)")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (8, 888)")
        db.con.execute(
            "INSERT INTO drug_exposure VALUES (5, 206, 20, '2020-05-01', '2020-05-10', 50, NULL, 1, 10, 10, 777, 888, NULL, NULL, NULL, NULL)"
        )
        db.con.execute("INSERT INTO observation_period VALUES (5, '2019-01-01', '2021-12-31')")

        de = DrugExposure(
            codeset_id=2,
            route_concept_cs=ConceptSetSelection(codeset_id=7),
            dose_unit_cs=ConceptSetSelection(codeset_id=8),
        )
        tsql = DrugExposureSqlBuilder().get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, DrugExposureGlotBuilder().build_select(de)))
        assert rows_a == rows_b, "DE with route/dose CS: rows differ"

    def test_with_occurrence_dates_and_route_cs(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import ConceptSetSelection, DateRange

        db.con.execute("DELETE FROM Codesets")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (2, 20)")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (7, 777)")

        de = DrugExposure(
            codeset_id=2,
            occurrence_start_date=DateRange(op="gte", value="2020-02-01"),
            occurrence_end_date=DateRange(op="lte", value="2020-06-01"),
            route_concept_cs=ConceptSetSelection(codeset_id=7),
        )
        tsql = DrugExposureSqlBuilder().get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, DrugExposureGlotBuilder().build_select(de)))
        assert rows_a == rows_b, "DE with occurrence dates + route CS: rows differ"

    def test_with_refills_quantity_days_supply(self, db: DuckDBTestHelper):
        de = DrugExposure(
            codeset_id=2,
            refills=NumericRange(op="gte", value=1),
            quantity=NumericRange(op="gte", value=5),
            days_supply=NumericRange(op="lte", value=15),
        )
        tsql = DrugExposureSqlBuilder().get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, DrugExposureGlotBuilder().build_select(de)))
        assert rows_a == rows_b, "DE with refills/quantity/days_supply: rows differ"

    def test_with_date_adjustment_alt_start_end(self, db: DuckDBTestHelper):
        de = DrugExposure(
            codeset_id=2,
            date_adjustment=DateAdjustment(
                start_offset=2,
                end_offset=3,
                start_with="end_date",
                end_with="start_date",
            ),
        )
        tsql = DrugExposureSqlBuilder().get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, DrugExposureGlotBuilder().build_select(de)))
        assert rows_a == rows_b, "DE with alt date adjustment: rows differ"

    def test_with_all_optional_fields(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import ConceptSetSelection, DateRange
        from circe.vocabulary.concept import Concept

        db.con.execute("INSERT INTO provider VALUES (3, 300)")
        db.con.execute("INSERT INTO observation_period VALUES (7, '2019-01-01', '2021-12-31')")
        db.con.execute("INSERT INTO person VALUES (7, 1985, 8507, 0, 0)")
        db.con.execute(
            "INSERT INTO visit_occurrence VALUES (7, 7, 30, '2020-08-01', '2020-08-10', 500, 3, NULL, NULL)"
        )
        db.con.execute(
            "INSERT INTO drug_exposure VALUES (7, 209, 20, '2020-08-02', '2020-08-08', 50, 'stopped', 2, 10, 6, 777, 888, 3, 7, NULL, 'LOT001')"
        )
        db.con.execute("DELETE FROM Codesets")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (2, 20)")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (10, 999)")

        de = DrugExposure(
            codeset_id=2,
            drug_source_concept=10,
            occurrence_start_date=DateRange(op="gte", value="2020-08-01"),
            occurrence_end_date=DateRange(op="lte", value="2020-09-01"),
            drug_type=[Concept(concept_id=50)],
            drug_type_cs=ConceptSetSelection(codeset_id=2),
            route_concept=[Concept(concept_id=777)],
            dose_unit=[Concept(concept_id=888)],
            provider_specialty=[Concept(concept_id=300)],
            visit_type_cs=ConceptSetSelection(codeset_id=2),
            refills=NumericRange(op="gte", value=1),
            quantity=NumericRange(op="gte", value=5),
            days_supply=NumericRange(op="gte", value=5),
            age=NumericRange(op="gte", value=18),
        )
        tsql = DrugExposureSqlBuilder().get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, DrugExposureGlotBuilder().build_select(de)))
        assert rows_a == rows_b, "DE with all optional fields: rows differ"

    def test_with_source_concept_and_drug_type_cs(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import ConceptSetSelection

        db.con.execute("DELETE FROM Codesets")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (2, 20)")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (10, 99)")

        de = DrugExposure(
            codeset_id=2,
            drug_source_concept=10,
            drug_type_cs=ConceptSetSelection(codeset_id=2),
        )
        tsql = DrugExposureSqlBuilder().get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, DrugExposureGlotBuilder().build_select(de)))
        assert rows_a == rows_b, "DE with source concept + type CS: rows differ"

    def test_with_lot_number_text(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import TextFilter

        db.con.execute(
            "INSERT INTO drug_exposure VALUES (5, 207, 20, '2020-06-01', '2020-06-10', 50, NULL, 0, 5, 10, NULL, NULL, NULL, NULL, NULL, NULL)"
        )

        de = DrugExposure(
            codeset_id=2,
            lot_number=TextFilter(text="ABC", op="contains"),
            stop_reason=TextFilter(text="stopped", op="eq"),
        )
        tsql = DrugExposureSqlBuilder().get_criteria_sql(de)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, DrugExposureGlotBuilder().build_select(de)))
        assert rows_a == rows_b, "DE with text filters: rows differ"


class TestComprehensiveVisitOccurrence:
    """Exercise all optional VO fields: visit_type, place_of_service, provider, source concept, date adjustment, visit_length."""

    def test_with_visit_type_place_of_service(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import ConceptSetSelection

        db.con.execute("INSERT INTO care_site VALUES (1, 1000)")
        db.con.execute(
            "INSERT INTO visit_occurrence VALUES (5, 5, 30, '2020-05-01', '2020-05-10', 500, NULL, 1, NULL)"
        )
        db.con.execute("INSERT INTO observation_period VALUES (5, '2019-01-01', '2021-12-31')")
        db.con.execute("DELETE FROM Codesets")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (3, 30)")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (6, 500)")

        vo = VisitOccurrence(
            codeset_id=3,
            visit_type_cs=ConceptSetSelection(codeset_id=6),
            place_of_service_cs=ConceptSetSelection(codeset_id=6),
        )
        tsql = VisitOccurrenceSqlBuilder().get_criteria_sql(vo)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, VisitOccurrenceGlotBuilder().build_select(vo)))
        assert rows_a == rows_b, "VO with visit_type/place_of_service CS: rows differ"

    def test_with_visit_source_concept(self, db: DuckDBTestHelper):
        db.con.execute("DELETE FROM Codesets")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (3, 30)")
        db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (9, 999)")
        db.con.execute(
            "INSERT INTO visit_occurrence VALUES (5, 5, 30, '2020-05-01', '2020-05-10', 500, NULL, NULL, NULL)"
        )

        vo = VisitOccurrence(
            codeset_id=3,
            visit_source_concept=9,
        )
        tsql = VisitOccurrenceSqlBuilder().get_criteria_sql(vo)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, VisitOccurrenceGlotBuilder().build_select(vo)))
        assert rows_a == rows_b, "VO with visit_source_concept: rows differ"

    def test_with_visit_length_and_date_adjustment(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import NumericRange

        vo = VisitOccurrence(
            codeset_id=3,
            visit_length=NumericRange(op="gt", value=5),
            date_adjustment=DateAdjustment(
                start_offset=1, end_offset=2, start_with="END_DATE", end_with="START_DATE"
            ),
        )
        tsql = VisitOccurrenceSqlBuilder().get_criteria_sql(vo)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, VisitOccurrenceGlotBuilder().build_select(vo)))
        assert rows_a == rows_b, "VO with visit_length + date_adjustment: rows differ"

    def test_with_provider_specialty_and_gender(self, db: DuckDBTestHelper):
        from circe.vocabulary.concept import Concept

        db.con.execute("INSERT INTO provider VALUES (2, 200)")
        db.con.execute(
            "INSERT INTO visit_occurrence VALUES (6, 6, 30, '2020-07-01', '2020-07-15', 500, 2, NULL, NULL)"
        )
        db.con.execute(
            "INSERT INTO condition_occurrence VALUES (6, 107, 10, '2020-07-02', '2020-07-05', 100, NULL, 0, 6, 2, NULL)"
        )
        db.con.execute("INSERT INTO observation_period VALUES (6, '2019-01-01', '2021-12-31')")
        db.con.execute(
            "INSERT INTO drug_exposure VALUES (6, 208, 20, '2020-07-03', '2020-07-10', 50, NULL, 0, 5, 7, NULL, NULL, 2, 6, NULL, NULL)"
        )

        co = ConditionOccurrence(
            codeset_id=1,
            provider_specialty=[Concept(concept_id=200)],
            gender=[Concept(concept_id=8532)],
        )
        tsql = ConditionOccurrenceSqlBuilder().get_criteria_sql(co)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, ConditionOccurrenceGlotBuilder().build_select(co)))
        assert rows_a == rows_b, "CO with provider specialty + gender: rows differ"

    def test_with_place_of_service_and_gender(self, db: DuckDBTestHelper):
        from circe.vocabulary.concept import Concept

        db.con.execute("INSERT INTO care_site VALUES (1, 1000)")
        db.con.execute(
            "INSERT INTO visit_occurrence VALUES (6, 6, 30, '2020-07-01', '2020-07-15', 500, NULL, 1, NULL)"
        )
        db.con.execute("INSERT INTO observation_period VALUES (6, '2019-01-01', '2021-12-31')")

        vo = VisitOccurrence(
            codeset_id=3,
            place_of_service=[Concept(concept_id=1000)],
            gender=[Concept(concept_id=8532)],
        )
        tsql = VisitOccurrenceSqlBuilder().get_criteria_sql(vo)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, VisitOccurrenceGlotBuilder().build_select(vo)))
        assert rows_a == rows_b, "VO with place_of_service + gender: rows differ"

    def test_with_occurrence_dates_and_gender(self, db: DuckDBTestHelper):
        from circe.cohortdefinition import DateRange

        vo = VisitOccurrence(
            codeset_id=3,
            occurrence_start_date=DateRange(op="gte", value="2020-02-01"),
            occurrence_end_date=DateRange(op="lte", value="2020-06-01"),
        )
        tsql = VisitOccurrenceSqlBuilder().get_criteria_sql(vo)
        rows_a = _result_set(_normalize_dates(db.query(f"SELECT * FROM ({_sql_param_replace(tsql)}) C")))
        rows_b = _result_set(_run_glot(db, VisitOccurrenceGlotBuilder().build_select(vo)))
        assert rows_a == rows_b, "VO with occurrence dates: rows differ"
