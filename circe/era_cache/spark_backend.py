"""SQL-over-Thrift backend adapter.

The local Spark deployment exposes a Hive/Spark Thrift server on port 10000,
not a Spark Connect endpoint, so ibis cannot speak to it directly.  This module
provides a small ibis-like backend whose relations compile to Spark SQL and
execute over a Thrift connection.

Only the surface the era cache needs is implemented:

- ``table(name, database=...)`` to read a relation
- ``list_databases()`` / ``create_database()`` / ``drop_table()``
- ``raw_sql(sql)`` for DELETE and other statements
- ``execute(relation)`` to run a compiled SELECT

Expressions are built with ibis itself and compiled with the Spark dialect,
which keeps the cache logic backend-agnostic.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Callable
from typing import Any

import ibis

__all__ = ["ThriftBackend", "quote_identifier", "table_reference"]


_OPTIONS_READY = False


def _ensure_ibis_options() -> None:
    """Install ibis' PySpark options, which a real backend normally sets.

    The PySpark SQL compiler reads ``ibis.config.options.pyspark``.  Without a
    connected PySpark backend that value is ``None``, so this adapter installs
    the same single field the backend's own options object exposes.
    """
    global _OPTIONS_READY
    if _OPTIONS_READY:
        return
    try:
        from ibis.config import Config, options

        if getattr(options, "pyspark", None) is None:

            class _PySparkOptions(Config):
                treat_nan_as_null: bool = False

            options.pyspark = _PySparkOptions()
    except Exception:  # noqa: BLE001 - options are advisory
        pass
    _OPTIONS_READY = True


def quote_identifier(identifier: str) -> str:
    """Quote an identifier for Spark SQL."""
    return f"`{identifier.replace('`', '``')}`"


def table_reference(name: str, database: str | None) -> str:
    """Return ``database.name`` or ``name``, quoted."""
    if database:
        return f"{quote_identifier(database)}.{quote_identifier(name)}"
    return quote_identifier(name)


class _Connection:
    """Connection proxy exposing ``cursor()`` for backends that expect DBI."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def cursor(self) -> Any:
        return self._connection.cursor()

    def commit(self) -> None:
        return None


class ThriftBackend:
    """A minimal ibis-like backend over a Spark/Hive Thrift server."""

    name = "spark-thrift"

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 10000,
        username: str = "spark",
        database: str = "default",
        connection_factory: Callable[..., Any] | None = None,
        connect_retries: int = 4,
        operation_retries: int = 3,
    ) -> None:
        if connection_factory is None:
            from pyhive import hive  # imported lazily so the core package stays optional

            connection_factory = hive.Connection
        self.host = host
        self.port = port
        self.username = username
        self.database = database
        self._connection_factory = connection_factory
        self.connect_retries = connect_retries
        self.operation_retries = operation_retries
        self._connection: Any = None
        self._qualify: dict[str, str] = {}
        # Relations this large must not be broadcast; the planner would try.
        self.no_broadcast_tables: set[str] = set()

    # -- connection --------------------------------------------------------
    def _connect(self) -> Any:
        """Open a connection, retrying briefly while the server is saturated."""
        import time

        last: Exception | None = None
        for attempt in range(self.connect_retries):
            try:
                return self._connection_factory(
                    host=self.host,
                    port=self.port,
                    username=self.username,
                    database=self.database,
                )
            except Exception as exc:  # noqa: BLE001 - retry transport failures
                last = exc
                time.sleep(min(2**attempt, 15))
        assert last is not None
        raise last

    def _conn(self) -> Any:
        if self._connection is None:
            self._connection = self._connect()
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
            finally:
                self._connection = None

    # -- execution ---------------------------------------------------------
    def _reset(self) -> None:
        """Drop a dead connection so the next call reconnects."""
        connection = self._connection
        self._connection = None
        if connection is not None:
            with contextlib.suppress(Exception):
                connection.close()

    @staticmethod
    def _is_transport_error(exc: Exception) -> bool:
        name = type(exc).__name__
        text = str(exc)
        return (
            "Transport" in name
            or "read 0 bytes" in text
            or "Broken pipe" in text
            or "Connection reset" in text
        )

    def _retry(self, operation: Any) -> Any:
        """Run an operation, reconnecting if the session has gone away.

        Long statements can outlive the Thrift session on a busy server, so a
        dropped transport is retried rather than surfaced.  The retry count is
        bounded to avoid masking a genuinely unreachable server.
        """
        attempts = max(1, self.operation_retries)
        last: Exception | None = None
        for attempt in range(attempts):
            try:
                return operation()
            except Exception as exc:  # noqa: BLE001 - only transport errors retry
                if not self._is_transport_error(exc):
                    raise
                last = exc
                self._reset()
                if attempt + 1 < attempts:
                    import time

                    time.sleep(min(2**attempt, 20))
        assert last is not None
        raise last

    def raw_sql(self, sql: str) -> list[tuple[Any, ...]]:
        """Run a statement and return rows (empty for DDL/DML)."""

        def _run() -> list[tuple[Any, ...]]:
            return self.raw_sql_raw(sql)

        return self._retry(_run)  # type: ignore[no-any-return]

    def _run_with_settings(self, statement: str) -> None:
        """Run a DDL/DML statement after applying session settings.

        Settings are sent as their own statement because Spark cannot combine a
        ``SET`` with an ``INSERT INTO ... SELECT`` in one Thrift call.
        """
        if self._needs_sort_merge(statement):
            self.raw_sql("SET spark.sql.autoBroadcastJoinThreshold=-1")
        self.raw_sql_raw(statement)

    def raw_sql_raw(self, sql: str) -> list[tuple[Any, ...]]:
        """Execute exactly *sql*, with no session-setting prefixing."""

        def _run() -> list[tuple[Any, ...]]:
            cursor = self._conn().cursor()
            cursor.execute(sql)
            with contextlib.suppress(Exception):
                return list(cursor.fetchall())
            return []

        return self._retry(_run)  # type: ignore[no-any-return]

    def execute_statements(self, sql: str) -> Any:
        """Execute several ``;``-separated statements; return the last result.

        Used for session settings that must precede a query (for example
        disabling broadcast joins for very large cache tables).
        """
        statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
        frame = None
        for statement in statements[:-1]:
            self.raw_sql(statement)
        if statements:
            frame = self.execute_raw(statements[-1])
        return frame

    def execute_raw(self, sql: str) -> Any:
        """Execute a raw SELECT and return a pandas DataFrame."""
        import pandas as pd

        def _run() -> Any:
            if self._needs_sort_merge(sql):
                self.raw_sql_raw("SET spark.sql.autoBroadcastJoinThreshold=-1")
            cursor = self._conn().cursor()
            cursor.execute(sql)
            columns = [description[0] for description in cursor.description] if cursor.description else []
            return pd.DataFrame(cursor.fetchall(), columns=columns)

        return self._retry(_run)

    def execute(self, relation: Any) -> Any:
        """Execute an ibis relation and return a pandas DataFrame."""
        return self.execute_raw(self.compile(relation))

    def compile(self, relation: Any) -> str:
        """Compile an ibis relation to Spark SQL, qualifying table names."""
        _ensure_ibis_options()
        sql = str(ibis.to_sql(relation, dialect="pyspark"))
        for name, target in getattr(self, "_qualify", {}).items():
            quoted = f"`{name}`"
            if quoted in sql:
                sql = sql.replace(quoted, target)
        return sql

    def compile_write(self, relation: Any) -> str:
        """Compile a relation for INSERT or CTAS without a session-setting prefix."""
        return self.compile(relation)

    def _needs_sort_merge(self, sql: str) -> bool:
        return any(table in sql for table in self.no_broadcast_tables)

    def _with_session_settings(self, sql: str) -> str:
        """Prefix a statement with settings that must hold for its execution."""
        if self._needs_sort_merge(sql):
            return "SET spark.sql.autoBroadcastJoinThreshold=-1;\n" + sql
        return sql

    # -- schema inspection -------------------------------------------------
    def table(self, name: str, database: str | None = None) -> Any:
        inner = ibis.table(self._schema_for(name, database), name=name)
        target = table_reference(name, database)
        self._qualify[name] = target
        return _TableProxy(inner, target)

    def _schema_for(self, name: str, database: str | None) -> Any:
        cursor = self._conn().cursor()
        cursor.execute(f"DESCRIBE {table_reference(name, database)}")
        columns: dict[str, str] = {}
        for row in cursor.fetchall():
            column = row[0]
            dtype = row[1]
            if not column or column.startswith("#"):
                continue
            columns[column] = _map_type(dtype)
        if not columns:
            raise ValueError(f"Table {table_reference(name, database)} has no columns.")
        return ibis.schema(list(columns.items()))

    def list_databases(self) -> list[str]:
        return [row[0] for row in self.raw_sql("SHOW DATABASES")]

    def create_database(self, name: str) -> None:
        self.raw_sql(f"CREATE DATABASE IF NOT EXISTS {quote_identifier(name)}")

    def list_tables(self, database: str | None = None) -> list[str]:
        target = quote_identifier(database) if database else ""
        return [row[1] for row in self.raw_sql(f"SHOW TABLES IN {target}")]

    def drop_table(self, name: str, database: str | None = None, force: bool = False) -> None:
        del force
        self.raw_sql(f"DROP TABLE IF EXISTS {table_reference(name, database)}")
        self._qualify.pop(name, None)

    def table_exists(self, name: str, database: str | None = None) -> bool:
        target = quote_identifier(database) if database else ""
        try:
            rows = self.raw_sql(f"SHOW TABLES IN {target} LIKE '{name}'")
        except Exception:  # noqa: BLE001
            return False
        return any(row[1] == name for row in rows)

    # -- writes ------------------------------------------------------------
    def create_table(
        self,
        name: str,
        obj: Any = None,
        *,
        schema: Any | None = None,
        database: str | None = None,
        temp: bool = False,
        overwrite: bool = False,
    ) -> None:
        del temp
        target = table_reference(name, database)
        if overwrite:
            self.raw_sql(f"DROP TABLE IF EXISTS {target}")
        if obj is not None:
            statement = f"CREATE TABLE {target} USING DELTA AS {self.compile_write(obj)}"
            self._run_with_settings(statement)
            return
        if schema is None:
            raise ValueError("create_table requires either obj or schema.")
        columns = ", ".join(
            f"{quote_identifier(column)} {_to_spark_type(dtype)}" for column, dtype in dict(schema).items()
        )
        self.raw_sql(f"CREATE TABLE IF NOT EXISTS {target} ({columns})")

    def insert(self, name: str, obj: Any, *, database: str | None = None, overwrite: bool = False) -> None:
        """Append a relation, or replace the table when ``overwrite`` is set."""
        if overwrite:
            self.create_table(name, obj, database=database, overwrite=True)
            return
        target = table_reference(name, database)
        statement = f"INSERT INTO {target} {self.compile_write(obj)}"
        self._run_with_settings(statement)

    def memtable(self, data: Any, *, schema: Any | None = None) -> Any:
        """Build a relation from an in-memory table without touching the server."""
        if schema is not None:
            data = _coerce_schema(data, schema)
        return ibis.memtable(data)


class _TableProxy:
    """Wraps an ibis table so compiled SQL uses the fully-qualified name.

    Reads are compiled first against a bare table name and then qualified, so
    the backend does not need to know the catalog/database at compile time.
    """

    def __init__(self, expr: Any, target: str) -> None:
        self._expr = expr
        self._target = target

    def __getattr__(self, item: str) -> Any:
        return getattr(self._expr, item)

    def __getitem__(self, key: Any) -> Any:
        return self._expr[key]

    def __repr__(self) -> str:
        return f"Table({self._target})"


# -- type mapping ----------------------------------------------------------
_SPARK_TO_IBIS = {
    "int": "int64",
    "integer": "int64",
    "bigint": "int64",
    "smallint": "int64",
    "tinyint": "int64",
    "long": "int64",
    "double": "float64",
    "float": "float64",
    "decimal": "float64",
    "date": "date",
    "timestamp": "timestamp",
    "boolean": "boolean",
    "string": "string",
    "varchar": "string",
    "char": "string",
}

_IBIS_TO_SPARK = {
    "int64": "BIGINT",
    "int32": "INT",
    "float64": "DOUBLE",
    "float32": "FLOAT",
    "date": "DATE",
    "timestamp": "TIMESTAMP",
    "boolean": "BOOLEAN",
    "string": "STRING",
}


def _map_type(spark_type: str) -> str:
    base = re.split(r"[<(]", (spark_type or "").strip().lower())[0]
    return _SPARK_TO_IBIS.get(base, "string")


def _to_spark_type(dtype: str) -> str:
    return _IBIS_TO_SPARK.get(dtype, "STRING")


def _coerce_schema(data: Any, schema: Any) -> Any:
    """Best-effort dtype coercion for small in-memory frames."""
    try:
        import pandas as pd

        frame = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        mapping = dict(schema.items()) if hasattr(schema, "items") else dict(schema)
        for column, dtype in mapping.items():
            if column in frame:
                if dtype == "date":
                    frame[column] = pd.to_datetime(frame[column]).dt.date
                elif dtype == "string":
                    frame[column] = frame[column].astype("string")
                elif dtype == "int64":
                    frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
                elif dtype == "float64":
                    frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("float64")
        return frame
    except Exception:  # noqa: BLE001 - coercion is best effort
        return data
