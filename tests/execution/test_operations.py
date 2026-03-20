from __future__ import annotations

from types import SimpleNamespace

import pytest

from circe.execution.errors import ExecutionError
from circe.execution.ibis.operations import (
    _catalog_db_tuple,
    _run_transaction_control,
    cohort_rows_exist,
    create_table,
    delete_cohort_rows,
    exclude_cohort_rows,
    insert_relation,
    read_table,
    replace_cohort_rows_transactionally,
    supports_transactional_replace,
    table_exists,
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


class _ListTablesBackend:
    def __init__(self, tables: list[str], *, reject_database: bool = False):
        self.tables = tables
        self.reject_database = reject_database
        self.calls: list[str | None] = []

    def list_tables(self, database=None):
        self.calls.append(database)
        if self.reject_database and database is not None:
            raise TypeError("database kwarg not supported")
        return self.tables


class _TableBackend:
    def __init__(self, relation=None, *, fail: bool = False):
        self.relation = relation
        self.fail = fail

    def table(self, name, database=None):
        if self.fail:
            raise RuntimeError("boom")
        return self.relation


class _CohortColumn:
    def cast(self, _dtype):
        return self

    def __eq__(self, other):
        return ("eq", other)

    def __ne__(self, other):
        return ("ne", other)


class _CohortRelation:
    cohort_definition_id = _CohortColumn()

    def __init__(self, rows, *, fail_filter: bool = False):
        self.rows = rows
        self.fail_filter = fail_filter

    def filter(self, _predicate):
        if self.fail_filter:
            raise RuntimeError("boom")
        return self

    def limit(self, _count):
        return self

    def execute(self):
        return self.rows


class _RawSqlBackend:
    compiler = SimpleNamespace(quoted=False)

    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls: list[object] = []

    def raw_sql(self, statement):
        self.calls.append(statement)
        if self.fail:
            raise RuntimeError("boom")


class _CatalogBackend:
    def _to_sqlglot_table(self, schema):
        return f"table:{schema}"

    def _to_catalog_db_tuple(self, table):
        assert table.startswith("table:")
        return ("catalog", "database")


class _BrokenCatalogBackend:
    def _to_sqlglot_table(self, _schema):
        raise RuntimeError("boom")


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


def test_table_exists_uses_list_tables_with_database_fallback():
    backend = _ListTablesBackend(["cohort_out"], reject_database=True)

    assert table_exists(backend, table_name="cohort_out", schema="main") is True
    assert backend.calls == ["main", None]


def test_table_exists_falls_back_to_read_table_when_list_tables_is_unavailable():
    assert table_exists(_TableBackend(object()), table_name="cohort_out", schema="main") is True
    assert table_exists(_TableBackend(fail=True), table_name="cohort_out", schema="main") is False


def test_cohort_rows_exist_returns_true_and_false_from_relation():
    assert (
        cohort_rows_exist(
            _TableBackend(_CohortRelation([{"cohort_definition_id": 5}])),
            cohort_table="cohort_out",
            results_schema="main",
            cohort_id=5,
        )
        is True
    )
    assert (
        cohort_rows_exist(
            _TableBackend(_CohortRelation([])),
            cohort_table="cohort_out",
            results_schema="main",
            cohort_id=5,
        )
        is False
    )


def test_cohort_rows_exist_wraps_relation_errors():
    with pytest.raises(ExecutionError, match="failed checking existing rows for cohort_id=5"):
        cohort_rows_exist(
            _TableBackend(_CohortRelation([], fail_filter=True)),
            cohort_table="cohort_out",
            results_schema="main",
            cohort_id=5,
        )


def test_delete_cohort_rows_requires_raw_sql_support():
    with pytest.raises(ExecutionError, match="does not support raw_sql for cohort-table deletes"):
        delete_cohort_rows(
            object(),
            cohort_table="cohort_out",
            results_schema="main",
            cohort_id=5,
        )


def test_delete_cohort_rows_wraps_backend_failures():
    with pytest.raises(ExecutionError, match="failed deleting existing cohort rows"):
        delete_cohort_rows(
            _RawSqlBackend(fail=True),
            cohort_table="cohort_out",
            results_schema="main",
            cohort_id=5,
        )


def test_supports_transactional_replace_only_for_supported_backends():
    assert supports_transactional_replace(SimpleNamespace(name="duckdb")) is True
    assert supports_transactional_replace(SimpleNamespace(name="postgres")) is True
    assert supports_transactional_replace(SimpleNamespace(name="sqlite")) is False


def test_replace_cohort_rows_transactionally_rejects_unsupported_backends():
    with pytest.raises(ExecutionError, match="does not support transactional cohort-table replace"):
        replace_cohort_rows_transactionally(
            object(),
            backend=SimpleNamespace(name="sqlite"),
            cohort_table="cohort_out",
            results_schema="main",
            cohort_id=5,
        )


def test_exclude_cohort_rows_wraps_filter_errors():
    with pytest.raises(ExecutionError, match="failed removing existing rows for cohort_id=5"):
        exclude_cohort_rows(_CohortRelation([], fail_filter=True), cohort_id=5)


def test_run_transaction_control_requires_raw_sql_support():
    with pytest.raises(ExecutionError, match="does not support raw_sql for transactional cohort writes"):
        _run_transaction_control(object(), "BEGIN")


def test_run_transaction_control_wraps_backend_errors():
    with pytest.raises(ExecutionError, match="failed executing transaction statement 'BEGIN'"):
        _run_transaction_control(_RawSqlBackend(fail=True), "BEGIN")


def test_catalog_db_tuple_uses_backend_helpers_and_falls_back_cleanly():
    assert _catalog_db_tuple(_CatalogBackend(), "results") == ("catalog", "database")
    assert _catalog_db_tuple(_BrokenCatalogBackend(), "results") == (None, "results")
    assert _catalog_db_tuple(object(), None) == (None, None)
