from __future__ import annotations

from types import SimpleNamespace

import pytest

from circe.execution.errors import ExecutionError
from circe.execution.ibis.operations import (
    create_table,
    insert_relation,
    read_table,
    replace_cohort_rows_transactionally,
)


class _Backend:
    name = "duckdb"
    compiler = SimpleNamespace(quoted=False)

    def __init__(self, *, fail_insert: bool = False):
        self.fail_insert = fail_insert
        self.events: list[tuple[str, object]] = []

    def raw_sql(self, query):
        sql = query.sql("duckdb") if hasattr(query, "sql") else query
        self.events.append(("sql", sql))

    def insert(self, name, obj, *, database=None, overwrite=False):
        self.events.append(("insert", name, database, overwrite))
        if self.fail_insert:
            raise RuntimeError("boom")


class _SchemaFallbackBackend:
    def __init__(self):
        self.calls: list[tuple[str, object, object]] = []

    def table(self, name, database=None):
        self.calls.append(("table", name, database))
        if database is not None:
            raise TypeError("database kwarg not supported")
        return (name, None)

    def create_table(self, name, *, obj=None, database=None, overwrite=False, temp=False):
        self.calls.append(("create_table", name, database))
        if database is not None:
            raise TypeError("database kwarg not supported")
        return None

    def insert(self, name, obj, *, database=None, overwrite=False):
        self.calls.append(("insert", name, database))
        if database is not None:
            raise TypeError("database kwarg not supported")
        return None


def test_replace_cohort_rows_transactionally_commits_on_success():
    backend = _Backend()

    replace_cohort_rows_transactionally(
        object(),
        backend=backend,
        cohort_table="cohort_out",
        results_schema="main",
        cohort_id=5,
    )

    assert backend.events[0] == ("sql", "BEGIN")
    assert backend.events[1][0] == "sql"
    assert "DELETE FROM main.cohort_out WHERE cohort_definition_id = 5" in backend.events[1][1]
    assert backend.events[2] == ("insert", "cohort_out", "main", False)
    assert backend.events[3] == ("sql", "COMMIT")


def test_replace_cohort_rows_transactionally_rolls_back_on_insert_failure():
    backend = _Backend(fail_insert=True)

    with pytest.raises(ExecutionError, match="failed inserting relation into table 'cohort_out'"):
        replace_cohort_rows_transactionally(
            object(),
            backend=backend,
            cohort_table="cohort_out",
            results_schema="main",
            cohort_id=5,
        )

    assert backend.events[0] == ("sql", "BEGIN")
    assert backend.events[1][0] == "sql"
    assert backend.events[2] == ("insert", "cohort_out", "main", False)
    assert backend.events[3] == ("sql", "ROLLBACK")


def test_read_table_falls_back_when_backend_rejects_database_kwarg():
    backend = _SchemaFallbackBackend()

    result = read_table(
        backend,
        table_name="cohort_out",
        schema="main",
    )

    assert result == ("cohort_out", None)
    assert backend.calls == [
        ("table", "cohort_out", "main"),
        ("table", "cohort_out", None),
    ]


def test_create_table_falls_back_when_backend_rejects_database_kwarg():
    backend = _SchemaFallbackBackend()

    create_table(
        backend,
        table_name="cohort_out",
        schema="main",
        obj=object(),
        overwrite=True,
    )

    assert backend.calls == [
        ("create_table", "cohort_out", "main"),
        ("create_table", "cohort_out", None),
    ]


def test_insert_relation_falls_back_when_backend_rejects_database_kwarg():
    backend = _SchemaFallbackBackend()

    insert_relation(
        object(),
        backend=backend,
        target_table="cohort_out",
        target_schema="main",
    )

    assert backend.calls == [
        ("insert", "cohort_out", "main"),
        ("insert", "cohort_out", None),
    ]
