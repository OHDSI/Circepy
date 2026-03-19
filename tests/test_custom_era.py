"""Tests for custom era implementation using SQLGlot transpilation."""

import pytest

pytest.importorskip("ibis")
pytest.importorskip("sqlglot")


import ibis

from circe.execution.engine.custom_era import (
    build_custom_era_sql,
    generate_custom_era_sql_reference,
    get_backend_dialect,
    transpile_custom_era_sql,
    validate_custom_era_support,
)
from circe.execution.errors import CompilationError, UnsupportedFeatureError


class TestDialectMapping:
    """Test backend to dialect mapping."""

    def test_get_backend_dialect_duckdb(self):
        """DuckDB backend should map to duckdb dialect."""

        # Create a mock backend with name attribute
        class MockBackend:
            name = "duckdb"

        backend = MockBackend()
        assert get_backend_dialect(backend) == "duckdb"

    def test_get_backend_dialect_postgres(self):
        """PostgreSQL backend should map to postgres dialect."""

        class MockBackend:
            name = "postgres"

        backend = MockBackend()
        assert get_backend_dialect(backend) == "postgres"

    def test_get_backend_dialect_databricks(self):
        """Databricks backend should map to databricks dialect."""

        class MockBackend:
            name = "databricks"

        backend = MockBackend()
        assert get_backend_dialect(backend) == "databricks"

    def test_get_backend_dialect_spark(self):
        """Spark backend should map to databricks dialect."""

        class MockBackend:
            name = "spark"

        backend = MockBackend()
        assert get_backend_dialect(backend) == "databricks"

    def test_get_backend_dialect_unsupported(self):
        """Unsupported backend should raise UnsupportedFeatureError."""

        class MockBackend:
            name = "unsupported_db"

        backend = MockBackend()
        with pytest.raises(UnsupportedFeatureError, match="Custom era not supported"):
            get_backend_dialect(backend)


class TestReferenceSQLGeneration:
    """Test reference PostgreSQL SQL generation."""

    def test_generate_reference_sql_basic(self):
        """Reference SQL should contain expected components."""
        sql = generate_custom_era_sql_reference(
            events_table_name="test_schema.events",
            gap_days=30,
            offset_start=0,
            offset_end=0,
        )

        # Check for key SQL components
        assert "WITH event_gaps AS" in sql
        assert "era_boundaries AS" in sql
        assert "era_ids AS" in sql
        assert "LAG(start_date)" in sql
        assert "PARTITION BY person_id" in sql
        assert "SUM(is_new_era)" in sql
        assert "INTERVAL '30 days'" in sql
        assert "test_schema.events" in sql

    def test_generate_reference_sql_with_offsets(self):
        """Reference SQL should include offsets."""
        sql = generate_custom_era_sql_reference(
            events_table_name="events",
            gap_days=7,
            offset_start=10,
            offset_end=5,
        )

        assert "INTERVAL '7 days'" in sql
        assert "INTERVAL '10 days'" in sql  # offset_start
        assert "INTERVAL '5 days'" in sql  # offset_end

    def test_generate_reference_sql_negative_offset(self):
        """Reference SQL should handle negative offsets."""
        sql = generate_custom_era_sql_reference(
            events_table_name="events",
            gap_days=30,
            offset_start=-5,
            offset_end=-10,
        )

        # Negative offsets are still syntactically valid
        assert "INTERVAL '-5 days'" in sql
        assert "INTERVAL '-10 days'" in sql


class TestSQLTranspilation:
    """Test SQLGlot transpilation to different dialects."""

    def test_transpile_to_duckdb(self):
        """Transpilation to DuckDB should succeed."""
        reference = generate_custom_era_sql_reference("events", gap_days=30)
        transpiled = transpile_custom_era_sql(reference, "duckdb")

        assert len(transpiled) > 0
        assert "WITH" in transpiled
        # DuckDB should use INTERVAL syntax
        assert "INTERVAL" in transpiled

    def test_transpile_to_spark(self):
        """Transpilation to Spark should succeed."""
        reference = generate_custom_era_sql_reference("events", gap_days=30)
        transpiled = transpile_custom_era_sql(reference, "spark")

        assert len(transpiled) > 0
        assert "WITH" in transpiled

    def test_transpile_to_snowflake(self):
        """Transpilation to Snowflake should succeed."""
        reference = generate_custom_era_sql_reference("events", gap_days=30)
        transpiled = transpile_custom_era_sql(reference, "snowflake")

        assert len(transpiled) > 0
        assert "WITH" in transpiled

    def test_transpile_preserves_logic(self):
        """Transpiled SQL should preserve key logic components."""
        reference = generate_custom_era_sql_reference("events", gap_days=7)

        for dialect in ["duckdb", "postgres", "spark", "snowflake"]:
            transpiled = transpile_custom_era_sql(reference, dialect)

            # All dialects should preserve window function structure
            assert "LAG" in transpiled.upper()
            assert "PARTITION BY" in transpiled.upper()
            assert "SUM" in transpiled.upper()


class TestBuildCustomEraSQLIntegration:
    """Test full SQL building with backend integration."""

    def test_build_custom_era_sql_duckdb(self):
        """Build custom era SQL for DuckDB backend."""

        class MockBackend:
            name = "duckdb"

        backend = MockBackend()
        sql = build_custom_era_sql(
            backend=backend,
            events_table_name="test.events",
            gap_days=30,
            offset_start=0,
            offset_end=0,
        )

        assert len(sql) > 0
        assert "test.events" in sql or "test" in sql  # Table name should be present

    def test_build_custom_era_sql_invalid_gap_days(self):
        """Negative gap_days should raise error."""

        class MockBackend:
            name = "duckdb"

        backend = MockBackend()
        with pytest.raises(CompilationError, match="gap_days must be non-negative"):
            build_custom_era_sql(
                backend=backend,
                events_table_name="events",
                gap_days=-1,
            )

    def test_build_custom_era_sql_debug_mode(self, capsys):
        """Debug mode should print SQL."""

        class MockBackend:
            name = "postgres"

        backend = MockBackend()
        build_custom_era_sql(
            backend=backend,
            events_table_name="events",
            gap_days=30,
            debug=True,
        )

        captured = capsys.readouterr()
        assert "Reference SQL" in captured.out
        assert "Transpiled SQL" in captured.out


class TestValidateCustomEraSupport:
    """Test validation of custom era support."""

    def test_validate_support_duckdb(self):
        """DuckDB should be supported."""

        class MockBackend:
            name = "duckdb"

        assert validate_custom_era_support(MockBackend())

    def test_validate_support_postgres(self):
        """PostgreSQL should be supported."""

        class MockBackend:
            name = "postgres"

        assert validate_custom_era_support(MockBackend())

    def test_validate_support_databricks(self):
        """Databricks should be supported."""

        class MockBackend:
            name = "databricks"

        assert validate_custom_era_support(MockBackend())

    def test_validate_support_unsupported(self):
        """Unsupported backends should return False."""

        class MockBackend:
            name = "unsupported_db"

        assert not validate_custom_era_support(MockBackend())


@pytest.mark.integration
class TestCustomEraExecution:
    """Integration tests with real Ibis backends."""

    @pytest.fixture
    def duckdb_backend(self):
        """Create DuckDB backend with test data."""
        con = ibis.duckdb.connect(":memory:")

        # Create test events table
        test_data = ibis.memtable(
            {
                "person_id": [1, 1, 1, 2, 2],
                "start_date": ["2020-01-01", "2020-01-05", "2020-01-15", "2020-02-01", "2020-02-10"],
                "end_date": ["2020-01-01", "2020-01-05", "2020-01-15", "2020-02-01", "2020-02-10"],
            }
        )

        # Cast dates properly
        test_data = test_data.mutate(
            start_date=test_data.start_date.cast("date"),
            end_date=test_data.end_date.cast("date"),
        )

        con.create_table("test_events", test_data, overwrite=True)
        return con

    def test_custom_era_basic_execution(self, duckdb_backend):
        """Test basic custom era execution."""
        # Build SQL for gap_days=7 (should group events 1-5 together, separate from 15)
        sql = build_custom_era_sql(
            backend=duckdb_backend,
            events_table_name="test_events",
            gap_days=7,
            offset_start=0,
            offset_end=0,
        )

        # Execute SQL
        result = duckdb_backend.sql(sql)
        df = result.execute()

        # Should have eras grouped by person and gap
        assert len(df) > 0
        assert "person_id" in df.columns
        assert "start_date" in df.columns
        assert "end_date" in df.columns

    def test_generate_sql_is_valid_postgres(self):
        """Generated PostgreSQL SQL should be syntactically valid."""
        sql = generate_custom_era_sql_reference("test_events", gap_days=30)

        # Try to parse with SQLGlot to validate syntax
        from sqlglot import parse

        parsed = parse(sql, dialect="postgres")
        assert len(parsed) > 0
        assert parsed[0] is not None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_events_table(self):
        """Custom era should handle empty events table."""
        # This is more of a documentation test - actual behavior depends on SQL execution
        sql = generate_custom_era_sql_reference("empty_events", gap_days=30)
        assert "empty_events" in sql

    def test_single_event_per_person(self):
        """Custom era should handle single event per person."""
        # SQL should still be valid
        sql = generate_custom_era_sql_reference("events", gap_days=30)
        assert "LAG" in sql  # LAG will return NULL for first row, handled by CASE

    def test_zero_gap_days(self):
        """Zero gap days should be valid (each event is own era)."""
        sql = generate_custom_era_sql_reference("events", gap_days=0)
        assert "INTERVAL '0 days'" in sql

    def test_large_gap_days(self):
        """Large gap days should be handled."""
        sql = generate_custom_era_sql_reference("events", gap_days=365)
        assert "INTERVAL '365 days'" in sql
