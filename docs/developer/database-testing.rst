Database Platform Testing
========================

CIRCEpy generates SQL for, and can execute cohorts on, the database platforms
that HADES supports.  The test suite mirrors the `HADES supported platforms
matrix <https://ohdsi.github.io/Hades/supportedPlatforms.html>`_ so that a
platform regression is caught before it reaches users.

Oracle is intentionally excluded.  HADES still exercises it, but CIRCEpy treats
Oracle as a legacy target.  The deprecated HADES targets (Hive, Impala, Netezza
and PDW) are not part of the matrix either; their SQL Renderer patterns remain
for backwards compatibility.

Coverage matrix
---------------

.. list-table::
   :header-rows: 1

   * - Platform
     - HADES CI
     - SQL Renderer
     - Ibis compile
     - Live execution
   * - PostgreSQL
     - yes
     - yes
     - yes
     - yes (CI)
   * - SQL Server
     - yes
     - yes
     - yes
     - yes (CI, non-blocking)
   * - Amazon Redshift
     - yes
     - yes
     - Postgres compiler
     - opt-in
   * - SQLite
     - yes
     - yes
     - yes (SQLite >= 3.46)
     - opt-in
   * - DuckDB
     - yes
     - yes
     - yes
     - yes (CI)
   * - InterSystems IRIS
     - yes
     - yes
     - n/a
     - n/a
   * - Snowflake
     - no
     - yes
     - yes
     - opt-in
   * - Apache Spark
     - no
     - yes
     - Databricks compiler
     - opt-in
   * - Azure Synapse
     - no
     - yes
     - SQL Server compiler
     - opt-in
   * - Google BigQuery
     - no
     - yes
     - yes
     - opt-in

The matrix definitions live in ``tests/execution/_database_matrix.py``.

Test layers
-----------

Dialect coverage (no server required)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``tests/test_database_dialects.py`` runs in the normal test suite.  It takes a
feature-rich cohort definition and checks both SQL-producing paths for every
platform:

* ``build_cohort_query()`` -> ``render()`` -> ``translate()`` for the SQL
  Renderer path, including a ``sqlglot`` parse for dialects that ``sqlglot``
  understands.
* ``build_cohort()`` -> ``ibis.to_sql(dialect=...)`` for the execution engine's
  native compilation path.

This catches missing dialect patterns and backend-specific expression
regressions without needing credentials.

Live execution contract
~~~~~~~~~~~~~~~~~~~~~~~

``tests/execution/test_database_backends.py`` is marked ``integration``.  It
seeds a small CDM into an isolated schema and checks the same cohort semantics
on every available backend: primary criteria, age filters, inclusion rules,
date-offset end strategies, lazy versus materialized builds, and
``write_cohort()`` duplicate/replace behaviour.

DuckDB always runs.  Every other backend is opt-in through environment
variables:

.. list-table::
   :header-rows: 1

   * - Backend
     - Variables
   * - PostgreSQL
     - ``CIRCE_TEST_POSTGRES_URL`` (for example
       ``postgresql://user:pass@localhost:5432/circe_test``)
   * - SQL Server / Synapse
     - ``CIRCE_TEST_MSSQL_URL``, optionally ``CIRCE_TEST_MSSQL_DRIVER``
       (default ``ODBC Driver 18 for SQL Server``) and
       ``CIRCE_TEST_MSSQL_TRUST_CERT=0``; a Synapse dedicated-SQL endpoint can
       use the same variable
   * - SQLite
     - ``CIRCE_TEST_SQLITE_PATH`` (default ``:memory:``); requires SQLite >= 3.46
   * - Amazon Redshift
     - ``CIRCE_TEST_REDSHIFT_URL`` (PostgreSQL wire protocol)
   * - Snowflake
     - ``CIRCE_TEST_SNOWFLAKE_URL``
   * - BigQuery
     - ``CIRCE_TEST_BIGQUERY_PROJECT`` and ``CIRCE_TEST_BIGQUERY_DATASET``
   * - Databricks / Spark
     - ``CIRCE_TEST_DATABRICKS_SERVER_HOSTNAME``,
       ``CIRCE_TEST_DATABRICKS_HTTP_PATH`` and
       ``CIRCE_TEST_DATABRICKS_TOKEN``

Install the matching Ibis extra before running a backend, for example:

.. code-block:: bash

   pip install -e ".[dev,ibis-postgres,ibis-mssql]"
   CIRCE_TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/circe_test \
       pytest tests/execution/test_database_backends.py -m integration

CI
--

``.github/workflows/database-tests.yml`` runs the dialect tests and starts
PostgreSQL and SQL Server service containers for the live contract.  The SQL
Server job is marked non-blocking while the ODBC service setup is validated;
remove ``continue-on-error`` once it has a stable history.

SQLite is compiled but not executed in CI: the runner's SQLite is older than
3.46, and Ibis refuses to compile date arithmetic below that version even though
SQLite itself supports the generated ``DATE(..., '+N day')`` form.  The test is
skipped with that explanation and runs on any developer interpreter with a newer
SQLite.

Adding a platform
-----------------

1. Add a ``HadesPlatform`` entry in ``tests/execution/_database_matrix.py``
   with the SQL Renderer dialect, Ibis dialect (if any), ``sqlglot`` dialect and
   HADES CI status.
2. Add a ``BackendConfig`` connector and environment variable if live execution
   should be supported.
3. Extend the dialect table above and the workflow if the backend belongs in
   CI.
