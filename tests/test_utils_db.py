from typing import Any

import duckdb
import pytest
import sqlglot


class DuckDBTestHelper:
    """Helper class for running OHDSI SQL in DuckDB tests."""

    def __init__(self):
        self.con = duckdb.connect(":memory:")
        self._setup_schema()

    def _setup_schema(self):
        """Setup basic OMOP CDM schema structure."""
        # Create schema for CDM
        self.con.execute("CREATE SCHEMA IF NOT EXISTS main")

        # Create basic tables needed for tests (empty for now)
        # Note: We use specific types broadly compatible with CDM 5.3+

        # CDM Tables used by criteria
        tables = [
            "person",
            "observation_period",
            "visit_occurrence",
            "condition_occurrence",
            "drug_exposure",
            "procedure_occurrence",
            "device_exposure",
            "measurement",
            "observation",
            "death",
            "note",
            "specimen",
            "visit_detail",
            "cost",
            "payer_plan_period",
            "drug_era",
            "dose_era",
            "condition_era",
            "location",
            "care_site",
            "provider",
        ]

        for table in tables:
            # Create dummy tables with a few key columns to avoid "table not found" errors
            # The exact schema isn't strictly needed for parsing, but helps if we insert data later
            self.con.execute(f"CREATE TABLE IF NOT EXISTS {table} (person_id INTEGER)")

        # Create temp tables usually expected by OHDSI SQL
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS Codesets (codeset_id INTEGER, concept_id INTEGER)"
        )

    def translate_sql(self, sql: str) -> str:
        """Translate OHDSI SQL (T-SQL) to DuckDB SQL."""
        # Simple translation pipeline
        try:
            # Parse as T-SQL
            sqlglot.parse(sql, read="tsql")

            # Additional transformations if needed for DuckDB specific quirks
            # (e.g. date math, string formatting)

            # Generate as DuckDB
            # Note: We might need to handle specific OHDSI dialects like @cdm_database_schema

            # Replace basic parameters manually if not handled by sqlglot
            # OHDSI SQL uses @parameter logic often

            return sqlglot.transpile(sql, read="tsql", write="duckdb")[0]
        except Exception as e:
            print(f"FAILED SQL:\n{sql}")
            raise RuntimeError(f"Translation failed: {e}") from e

    def execute_query(self, sql: str):
        """Execute translated query."""
        # Remove OHDSI params for local testing BEFORE translation
        # This prevents sqlglot from treating them as variables/parameters
        sql_clean = sql.replace("@cdm_database_schema", "main")
        sql_clean = sql_clean.replace("@target_database_schema", "main")
        sql_clean = sql_clean.replace("@target_cohort_table", "cohort")
        sql_clean = sql_clean.replace("@vocabulary_database_schema", "main")
        sql_clean = sql_clean.replace("#Codesets", "Codesets")
        sql_clean = sql_clean.replace("JOIN Codesets", "INNER JOIN Codesets")

        translated = self.translate_sql(sql_clean)

        return self.con.execute(translated)

    def query(self, sql: str) -> list[Any]:
        """Execute and return results."""
        return self.execute_query(sql).fetchall()


@pytest.fixture(scope="module")
def duckdb_helper():
    return DuckDBTestHelper()
