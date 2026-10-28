"""Database-platform matrix for the cross-backend execution tests.

The target list mirrors the platforms in the HADES ``Supported Database
Platforms`` table (https://ohdsi.github.io/Hades/supportedPlatforms.html).
Oracle is deliberately excluded: HADES still tests it, but CIRCEpy treats it as
a legacy target.

Two kinds of coverage are built on top of this matrix:

* SQL generation -- every platform gets a translated cohort script and, where
  Ibis has a compiler for the dialect, a compiled ``build_cohort()`` relation.
  These tests need no database server and therefore run in the normal suite.
* Live execution -- a backend-agnostic contract suite runs against DuckDB and
  any server configured through ``CIRCE_TEST_*`` environment variables.  The
  server jobs in ``.github/workflows/database-tests.yml`` exercise PostgreSQL
  and SQL Server; cloud platforms can be enabled by exporting the same
  variables locally or in CI.

Connection URLs are intentionally environment-driven so that credentials never
live in the repository.  See ``docs/developer/database-testing.rst``.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import unquote, urlparse

import pytest


@dataclass(frozen=True)
class HadesPlatform:
    """A database platform supported by HADES."""

    key: str
    label: str
    #: Target dialect accepted by :func:`circe.sqlrender.translate`.
    sqlrender_dialect: str
    #: Dialect accepted by ``ibis.to_sql()``; ``None`` when Ibis has no compiler.
    ibis_dialect: str | None
    #: Dialect accepted by ``sqlglot.parse()``; ``None`` when unsupported.
    sqlglot_dialect: str | None
    #: Whether the HADES continuous integration exercises this platform.
    hades_ci: bool


#: Platforms from the HADES support matrix, minus Oracle.  Deprecated HADES
#: targets (Hive, Impala, Netezza, PDW) are not included either; CIRCEpy keeps
#: their SQL renderer patterns for backwards compatibility but they are not
#: actively supported platforms.
HADES_PLATFORMS: tuple[HadesPlatform, ...] = (
    HadesPlatform("postgresql", "PostgreSQL", "postgresql", "postgres", "postgres", True),
    HadesPlatform("sql_server", "SQL Server", "sql server", "mssql", "tsql", True),
    HadesPlatform("redshift", "Amazon Redshift", "redshift", "postgres", "redshift", True),
    HadesPlatform("sqlite", "SQLite", "sqlite", "sqlite", "sqlite", True),
    HadesPlatform("duckdb", "DuckDB", "duckdb", "duckdb", "duckdb", True),
    HadesPlatform("iris", "InterSystems IRIS", "iris", None, None, True),
    HadesPlatform("snowflake", "Snowflake", "snowflake", "snowflake", "snowflake", False),
    HadesPlatform("spark", "Apache Spark", "spark", "databricks", "spark", False),
    HadesPlatform("synapse", "Azure Synapse", "synapse", "mssql", "tsql", False),
    HadesPlatform("bigquery", "Google BigQuery", "bigquery", "bigquery", "bigquery", False),
)

HADES_PLATFORMS_BY_KEY: dict[str, HadesPlatform] = {platform.key: platform for platform in HADES_PLATFORMS}


def sqlite_supports_ibis_temporal_arithmetic() -> bool:
    """Return whether Ibis can compile date arithmetic for this interpreter.

    Ibis refuses to compile year/month/day shifts for SQLite < 3.46 even though
    the equivalent ``DATE(..., '+N day')`` form is older.  The gate is part of
    Ibis, so only run SQLite execution/compilation tests when the interpreter
    is new enough.
    """
    return sqlite3.sqlite_version_info >= (3, 46, 0)


# ---------------------------------------------------------------------------
# Live backend configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BackendConfig:
    """A live database backend used by the contract suite."""

    key: str
    platform: HadesPlatform
    connect: Callable[[], Any]
    #: Whether the backend supports schemas (SQLite does not).
    supports_schemas: bool = True


def _connect_duckdb() -> Any:
    ibis = pytest.importorskip("ibis")
    return ibis.duckdb.connect()


def _connect_sqlite() -> Any:
    ibis = pytest.importorskip("ibis")
    path = os.environ.get("CIRCE_TEST_SQLITE_PATH", ":memory:")
    return ibis.sqlite.connect(path)


def _connect_postgres() -> Any:
    ibis = pytest.importorskip("ibis")
    return ibis.connect(os.environ["CIRCE_TEST_POSTGRES_URL"])


def _connect_mssql() -> Any:
    ibis = pytest.importorskip("ibis")
    parsed = urlparse(os.environ["CIRCE_TEST_MSSQL_URL"])
    if not parsed.hostname:
        raise pytest.UsageError("CIRCE_TEST_MSSQL_URL must include a host")
    kwargs: dict[str, Any] = {
        "host": parsed.hostname,
        "port": parsed.port or 1433,
        "user": unquote(parsed.username) if parsed.username else None,
        "password": unquote(parsed.password) if parsed.password else None,
        "database": parsed.path.lstrip("/") or None,
        "driver": os.environ.get("CIRCE_TEST_MSSQL_DRIVER", "ODBC Driver 18 for SQL Server"),
    }
    if os.environ.get("CIRCE_TEST_MSSQL_TRUST_CERT", "1") not in {"0", "false", "False"}:
        kwargs["TrustServerCertificate"] = "yes"
    return ibis.mssql.connect(**kwargs)


def _connect_redshift() -> Any:
    # Redshift speaks the PostgreSQL wire protocol; Ibis can drive it through
    # the Postgres backend.  Redshift-specific SQL differences are covered by
    # the SQL Renderer tests.  Accept either ``redshift://`` or
    # ``postgresql://`` URLs.
    ibis = pytest.importorskip("ibis")
    url = os.environ["CIRCE_TEST_REDSHIFT_URL"]
    if url.startswith("redshift://"):
        url = "postgresql://" + url[len("redshift://") :]
    return ibis.connect(url)


def _connect_snowflake() -> Any:
    ibis = pytest.importorskip("ibis")
    return ibis.connect(os.environ["CIRCE_TEST_SNOWFLAKE_URL"])


def _connect_bigquery() -> Any:
    ibis = pytest.importorskip("ibis")
    return ibis.bigquery.connect(
        project_id=os.environ["CIRCE_TEST_BIGQUERY_PROJECT"],
        dataset_id=os.environ["CIRCE_TEST_BIGQUERY_DATASET"],
    )


def _connect_databricks() -> Any:
    from circe.execution import connect_databricks

    return connect_databricks(
        server_hostname=os.environ["CIRCE_TEST_DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["CIRCE_TEST_DATABRICKS_HTTP_PATH"],
        personal_access_token=os.environ["CIRCE_TEST_DATABRICKS_TOKEN"],
    )


def live_backend_configs() -> list[BackendConfig]:
    """Return the backends enabled for this test run.

    DuckDB is always available because it is a core dependency.  Every other
    backend is opt-in through its environment variable so that the default
    suite stays fast and credential-free.
    """
    configs = [BackendConfig("duckdb", HADES_PLATFORMS_BY_KEY["duckdb"], _connect_duckdb)]
    if sqlite_supports_ibis_temporal_arithmetic():
        configs.append(
            BackendConfig(
                "sqlite",
                HADES_PLATFORMS_BY_KEY["sqlite"],
                _connect_sqlite,
                supports_schemas=False,
            )
        )
    if os.environ.get("CIRCE_TEST_POSTGRES_URL"):
        configs.append(BackendConfig("postgresql", HADES_PLATFORMS_BY_KEY["postgresql"], _connect_postgres))
    if os.environ.get("CIRCE_TEST_MSSQL_URL"):
        configs.append(BackendConfig("sql_server", HADES_PLATFORMS_BY_KEY["sql_server"], _connect_mssql))
    if os.environ.get("CIRCE_TEST_REDSHIFT_URL"):
        configs.append(BackendConfig("redshift", HADES_PLATFORMS_BY_KEY["redshift"], _connect_redshift))
    if os.environ.get("CIRCE_TEST_SNOWFLAKE_URL"):
        configs.append(BackendConfig("snowflake", HADES_PLATFORMS_BY_KEY["snowflake"], _connect_snowflake))
    if os.environ.get("CIRCE_TEST_BIGQUERY_PROJECT") and os.environ.get("CIRCE_TEST_BIGQUERY_DATASET"):
        configs.append(BackendConfig("bigquery", HADES_PLATFORMS_BY_KEY["bigquery"], _connect_bigquery))
    if (
        os.environ.get("CIRCE_TEST_DATABRICKS_SERVER_HOSTNAME")
        and os.environ.get("CIRCE_TEST_DATABRICKS_HTTP_PATH")
        and os.environ.get("CIRCE_TEST_DATABRICKS_TOKEN")
    ):
        configs.append(BackendConfig("spark", HADES_PLATFORMS_BY_KEY["spark"], _connect_databricks))
    return configs


# ---------------------------------------------------------------------------
# Schema, fixture data and lifecycle
# ---------------------------------------------------------------------------


def quote_identifier(identifier: str, key: str) -> str:
    """Quote *identifier* for the backend identified by *key*."""
    if key in {"sql_server", "synapse"}:
        return "[" + identifier.replace("]", "]]") + "]"
    if key in {"bigquery", "spark", "databricks"}:
        return "`" + identifier.replace("`", "``") + "`"
    return '"' + identifier.replace('"', '""') + '"'


@dataclass
class BackendHarness:
    """A connected backend with an isolated schema and a tiny OMOP CDM."""

    key: str
    platform: HadesPlatform
    connection: Any
    schema: str
    supports_schemas: bool = True

    @property
    def cdm_schema(self) -> str:
        return self.schema

    def build(self, expression, **kwargs):
        from circe.execution import build_cohort

        return build_cohort(
            expression,
            backend=self.connection,
            cdm_schema=self.cdm_schema,
            results_schema=self.cdm_schema,
            **kwargs,
        )

    def write(self, expression, *, cohort_table: str, cohort_id: int, **kwargs):
        from circe.execution import write_cohort

        return write_cohort(
            expression,
            backend=self.connection,
            cdm_schema=self.cdm_schema,
            results_schema=self.cdm_schema,
            cohort_table=cohort_table,
            cohort_id=cohort_id,
            **kwargs,
        )


def _create_schema(connection: Any, key: str) -> str:
    schema = f"circe_test_{uuid.uuid4().hex[:10]}"
    quoted = quote_identifier(schema, key)
    connection.raw_sql(f"CREATE SCHEMA {quoted}")
    return schema


def _drop_schema(connection: Any, key: str, schema: str) -> None:
    quoted = quote_identifier(schema, key)
    with contextlib.suppress(Exception):
        if key in {"sql_server", "synapse"}:
            # SQL Server has no DROP SCHEMA ... CASCADE.
            for table in connection.list_tables(database=schema):
                with contextlib.suppress(Exception):
                    connection.drop_table(table, database=schema, force=True)
            connection.raw_sql(f"DROP SCHEMA {quoted}")
        else:
            connection.raw_sql(f"DROP SCHEMA {quoted} CASCADE")


def _create_cdm_table(connection: Any, schema: str | None, name: str, data: dict[str, list[Any]]) -> None:
    from circe.execution.ibis.operations import create_table

    ibis = pytest.importorskip("ibis")
    create_table(
        connection,
        table_name=name,
        schema=schema,
        obj=ibis.memtable(data),
        overwrite=True,
    )


def seed_cdm(connection: Any, schema: str | None) -> None:
    """Create a tiny, deterministic CDM shared by the contract tests.

    Four people are enough to exercise age filters, inclusion rules and end
    strategies without repeating the much larger fixtures used by the DuckDB
    semantic tests.

    * person 1 -- adult, entry event (111) and inclusion event (222)
    * person 2 -- child, entry event only (age filter rejects)
    * person 3 -- adult, entry event only (inclusion rule rejects)
    * person 4 -- adult, entry event and inclusion event, later onset
    """
    _create_cdm_table(
        connection,
        schema,
        "person",
        {
            "person_id": [1, 2, 3, 4],
            "year_of_birth": [1980, 2015, 1970, 1970],
            "gender_concept_id": [8507, 8507, 8532, 8532],
        },
    )
    _create_cdm_table(
        connection,
        schema,
        "observation_period",
        {
            "person_id": [1, 2, 3, 4],
            "observation_period_id": [10, 11, 12, 13],
            "observation_period_start_date": [date(2019, 1, 1)] * 4,
            "observation_period_end_date": [date(2021, 12, 31)] * 4,
        },
    )
    _create_cdm_table(
        connection,
        schema,
        "condition_occurrence",
        {
            "person_id": [1, 1, 2, 3, 4, 4],
            "condition_occurrence_id": [100, 101, 102, 103, 104, 105],
            "condition_concept_id": [111, 222, 111, 111, 111, 222],
            "condition_start_date": [
                date(2020, 1, 1),
                date(2020, 2, 1),
                date(2020, 1, 5),
                date(2020, 1, 6),
                date(2020, 3, 1),
                date(2020, 3, 2),
            ],
            "condition_end_date": [
                date(2020, 1, 2),
                date(2020, 2, 2),
                date(2020, 1, 6),
                date(2020, 1, 7),
                date(2020, 3, 2),
                date(2020, 3, 3),
            ],
        },
    )


@contextlib.contextmanager
def open_backend(config: BackendConfig) -> Iterator[BackendHarness]:
    """Connect, create an isolated schema, seed the CDM and clean up."""
    connection = config.connect()
    schema = "main"
    if config.supports_schemas:
        schema = _create_schema(connection, config.key)
    try:
        seed_cdm(connection, schema if config.supports_schemas else None)
        yield BackendHarness(
            key=config.key,
            platform=config.platform,
            connection=connection,
            schema=schema,
            supports_schemas=config.supports_schemas,
        )
    finally:
        if config.supports_schemas:
            _drop_schema(connection, config.key, schema)
        with contextlib.suppress(Exception):
            connection.disconnect()
