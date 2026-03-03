"""
Unit tests for circe.features.domain_tables — introspection-based domain specs.
"""

from __future__ import annotations

import pytest

from circe.features.domain_tables import (
    DomainSpec,
    domain_spec_from_criteria,
    get_domain_spec,
    list_domains,
)


class TestDomainIntrospection:
    """Test that DomainSpec is correctly derived from Criteria models."""

    def test_condition_occurrence_spec(self):
        spec = get_domain_spec("ConditionOccurrence")
        assert spec.table_name == "condition_occurrence"
        assert spec.concept_id_column == "condition_concept_id"
        assert spec.start_date_column == "condition_start_date"
        assert spec.end_date_column == "condition_end_date"
        assert spec.primary_key_column == "condition_occurrence_id"

    def test_drug_exposure_spec(self):
        spec = get_domain_spec("DrugExposure")
        assert spec.table_name == "drug_exposure"
        assert spec.concept_id_column == "drug_concept_id"
        assert spec.start_date_column == "drug_exposure_start_date"
        assert spec.end_date_column == "drug_exposure_end_date"
        assert "quantity" in spec.value_columns
        assert "days_supply" in spec.value_columns
        assert "refills" in spec.value_columns

    def test_measurement_spec(self):
        spec = get_domain_spec("Measurement")
        assert spec.table_name == "measurement"
        assert spec.concept_id_column == "measurement_concept_id"
        assert spec.start_date_column == "measurement_date"
        # Measurement has same start and end date
        assert spec.end_date_column == "measurement_date"
        assert "value_as_number" in spec.value_columns
        assert "range_low" in spec.value_columns
        assert "range_high" in spec.value_columns

    def test_observation_spec(self):
        spec = get_domain_spec("Observation")
        assert spec.table_name == "observation"
        assert "value_as_number" in spec.value_columns

    def test_visit_occurrence_spec(self):
        spec = get_domain_spec("VisitOccurrence")
        assert spec.table_name == "visit_occurrence"
        assert spec.concept_id_column == "visit_concept_id"
        assert spec.value_columns == []  # No NumericRange fields

    def test_death_spec(self):
        spec = get_domain_spec("Death")
        assert spec.table_name == "death"
        assert spec.concept_id_column == "cause_concept_id"
        assert spec.primary_key_column == "person_id"

    def test_condition_era_spec(self):
        spec = get_domain_spec("ConditionEra")
        assert spec.table_name == "condition_era"
        assert spec.start_date_column == "condition_era_start_date"
        assert spec.end_date_column == "condition_era_end_date"

    def test_unknown_domain_raises(self):
        with pytest.raises(ValueError, match="Unknown domain"):
            get_domain_spec("NonExistentDomain")

    def test_list_domains_includes_core(self):
        domains = list_domains()
        assert "ConditionOccurrence" in domains
        assert "Measurement" in domains
        assert "DrugExposure" in domains
        assert len(domains) >= 14

    def test_effective_end_date_differs(self):
        spec = get_domain_spec("ConditionOccurrence")
        assert spec.effective_end_date_column == "condition_end_date"

    def test_effective_end_date_same_as_start(self):
        spec = get_domain_spec("Measurement")
        # Measurement has start==end date
        assert spec.effective_end_date_column == spec.start_date_column

    def test_direct_introspection(self):
        """Verify domain_spec_from_criteria works directly."""
        from circe.cohortdefinition import ProcedureOccurrence
        criteria = ProcedureOccurrence()
        spec = domain_spec_from_criteria(criteria)
        assert spec.table_name == "procedure_occurrence"
        assert "quantity" in spec.value_columns


class TestGetDomainEventsWithDuckDB:
    """Integration tests using an in-memory DuckDB backend."""

    @pytest.fixture
    def duckdb_ctx(self):
        ibis = pytest.importorskip("ibis")
        _ = pytest.importorskip("duckdb")

        from circe.execution.build_context import BuildContext, CohortBuildOptions, CodesetResource

        conn = ibis.duckdb.connect()

        conn.create_table(
            "condition_occurrence",
            obj=ibis.memtable({
                "person_id": [1, 1, 2],
                "condition_occurrence_id": [101, 102, 103],
                "condition_concept_id": [440383, 440383, 201826],
                "condition_start_date": ["2020-01-15", "2020-06-01", "2020-03-10"],
                "condition_end_date": ["2020-01-20", "2020-06-05", "2020-03-15"],
                "condition_type_concept_id": [32817, 32817, 32817],
                "condition_status_concept_id": [0, 0, 0],
                "visit_occurrence_id": [1001, 1002, 1003],
            }),
            overwrite=True,
        )

        conn.create_table(
            "measurement",
            obj=ibis.memtable({
                "person_id": [1, 1, 2],
                "measurement_id": [201, 202, 203],
                "measurement_concept_id": [3038553, 3038553, 3038553],
                "measurement_date": ["2020-02-01", "2020-07-01", "2020-04-01"],
                "value_as_number": [28.5, 29.1, 24.3],
                "value_as_concept_id": [0, 0, 0],
                "range_low": [18.5, 18.5, 18.5],
                "range_high": [30.0, 30.0, 30.0],
                "measurement_type_concept_id": [32817, 32817, 32817],
                "unit_concept_id": [9529, 9529, 9529],
                "operator_concept_id": [0, 0, 0],
                "visit_occurrence_id": [1001, 1002, 1003],
            }),
            overwrite=True,
        )

        conn.create_table(
            "concept",
            obj=ibis.memtable({
                "concept_id": [440383, 201826, 3038553],
                "invalid_reason": ["", "", ""],
            }),
            overwrite=True,
        )
        conn.create_table(
            "concept_ancestor",
            obj=ibis.memtable({
                "ancestor_concept_id": [440383, 201826, 3038553],
                "descendant_concept_id": [440383, 201826, 3038553],
            }),
            overwrite=True,
        )
        conn.create_table(
            "concept_relationship",
            obj=ibis.memtable({
                "concept_id_1": [440383],
                "concept_id_2": [440383],
                "relationship_id": ["Maps to"],
                "invalid_reason": [""],
            }),
            overwrite=True,
        )

        codesets_table = ibis.memtable({
            "codeset_id": [1, 1],
            "concept_id": [440383, 201826],
        })
        resource = CodesetResource(table=codesets_table)
        options = CohortBuildOptions(materialize_stages=False, materialize_codesets=False)
        ctx = BuildContext(conn, options, resource)
        yield ctx
        ctx.close()

    def test_get_condition_events_retains_columns(self, duckdb_ctx):
        from circe.features.domain_tables import get_domain_events

        events = get_domain_events("ConditionOccurrence", duckdb_ctx)
        result = events.execute()
        assert len(result) == 3
        assert "condition_concept_id" in result.columns
        assert "condition_start_date" in result.columns
        assert "person_id" in result.columns

    def test_get_measurement_events_has_values(self, duckdb_ctx):
        from circe.features.domain_tables import get_domain_events

        events = get_domain_events("Measurement", duckdb_ctx)
        result = events.execute()
        assert len(result) == 3
        assert "value_as_number" in result.columns
        assert "measurement_concept_id" in result.columns

    def test_get_events_with_codeset_filter(self, duckdb_ctx):
        from circe.features.domain_tables import get_domain_events

        events = get_domain_events("ConditionOccurrence", duckdb_ctx, codeset_id=1)
        result = events.execute()
        assert len(result) == 3

    def test_get_events_with_explicit_columns(self, duckdb_ctx):
        from circe.features.domain_tables import get_domain_events

        events = get_domain_events(
            "ConditionOccurrence", duckdb_ctx,
            columns=["person_id", "condition_concept_id"]
        )
        result = events.execute()
        assert set(result.columns) == {"person_id", "condition_concept_id"}

    def test_temporal_window_filter(self, duckdb_ctx):
        ibis = pytest.importorskip("ibis")
        from circe.features.domain_tables import get_domain_events, get_domain_spec, apply_temporal_window

        events = get_domain_events("ConditionOccurrence", duckdb_ctx)
        spec = get_domain_spec("ConditionOccurrence")

        cohort = ibis.memtable({
            "subject_id": [1],
            "cohort_start_date": ["2020-03-01"],
        })

        windowed = apply_temporal_window(
            events, cohort, spec, window=(-90, 0),
            cohort_person_col="subject_id",
            cohort_date_col="cohort_start_date",
        )
        result = windowed.execute()
        # Person 1: Jan 15 = -46 days (in window), Jun 01 = +92 days (out)
        assert len(result) == 1
        assert "time_delta_days" in result.columns
