"""Tests against the live local Spark (Delta) CDM via the Thrift server.

These tests are skipped unless a Spark Thrift server is reachable at the
configured host/port.  They are integration tests: they read the real Synthea
CDM in the ``cdm`` schema and write only into a scratch cache schema.

Run explicitly with::

    pytest tests/era_cache/test_spark_thrift.py -m spark
"""

from __future__ import annotations

import os
import socket

import pytest

from circe.era_cache import (
    CohortEraSpec,
    EraFeatureSpec,
    build_era_cache,
    era_feature_key,
    load_cohort,
    prevalence,
)
from circe.era_cache.scope import cohort_scope
from circe.era_cache.spark_backend import ThriftBackend

SPARK_HOST = os.environ.get("CIRCE_SPARK_HOST", "127.0.0.1")
SPARK_PORT = int(os.environ.get("CIRCE_SPARK_PORT", "10000"))
CACHE_SCHEMA = os.environ.get("CIRCE_SPARK_CACHE_SCHEMA", "cdm_era_cache_test")

pytestmark = pytest.mark.spark


def _reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


pytest.importorskip("pyhive")


@pytest.fixture(scope="module")
def spark_backend():
    if not _reachable(SPARK_HOST, SPARK_PORT):
        pytest.skip(f"Spark Thrift server not reachable at {SPARK_HOST}:{SPARK_PORT}")
    from circe.era_cache.schema import LARGE_TABLES

    backend = ThriftBackend(host=SPARK_HOST, port=SPARK_PORT)
    backend.no_broadcast_tables.update(LARGE_TABLES)
    yield backend
    backend.close()


@pytest.fixture(scope="module")
def cdm_schema() -> str:
    return os.environ.get("CIRCE_SPARK_CDM_SCHEMA", "cdm")


@pytest.fixture(scope="module")
def vocab_schema() -> str:
    return os.environ.get("CIRCE_SPARK_VOCAB_SCHEMA", "vocab")


def test_thrift_backend_can_read_the_cdm(spark_backend, cdm_schema):
    table = spark_backend.table("person", cdm_schema)
    assert "person_id" in table.columns
    total = spark_backend.execute(table.count())
    assert int(total.iloc[0, 0]) > 0


def test_build_and_read_condition_features(spark_backend, cdm_schema, vocab_schema):
    specs = [
        EraFeatureSpec(name="t2dm", source_table="condition_occurrence", concept_ids=(201826,)),
        EraFeatureSpec(name="chf", source_table="condition_occurrence", concept_ids=(316139,)),
    ]
    outcome = build_era_cache(
        specs,
        backend=spark_backend,
        cache_schema=CACHE_SCHEMA,
        cdm_schema=cdm_schema,
        vocabulary_schema=vocab_schema,
        force=True,
        scope=cohort_scope(1, cohort_table="cohort"),
    )
    assert outcome.failed == []
    assert set(outcome.generated) == {era_feature_key(spec) for spec in specs}

    cache = spark_backend.table("era_feature_presence", CACHE_SCHEMA)
    rows = spark_backend.execute(cache.count())
    assert int(rows.iloc[0, 0]) > 0


def test_prevalence_is_reproducible_across_windows(spark_backend, cdm_schema, vocab_schema):
    specs = [
        EraFeatureSpec(name="t2dm", source_table="condition_occurrence", concept_ids=(201826,)),
        EraFeatureSpec(name="chf", source_table="condition_occurrence", concept_ids=(316139,)),
    ]
    build_era_cache(
        specs,
        backend=spark_backend,
        cache_schema=CACHE_SCHEMA,
        cdm_schema=cdm_schema,
        vocabulary_schema=vocab_schema,
        scope=cohort_scope(1, cohort_table="cohort"),
    )
    key_to_name = {era_feature_key(spec): spec.name for spec in specs}

    # Build a deterministic cohort: first T2DM occurrence in 2008-2009, a year
    # of follow-up.  The shipped cdm_results.cohort table is empty.
    cohort_table_name = "era_cache_demo_cohort"
    spark_backend.raw_sql(f"DROP TABLE IF EXISTS {CACHE_SCHEMA}.{cohort_table_name}")
    t2dm_key = era_feature_key(specs[0])
    spark_backend.raw_sql(
        f"CREATE TABLE {CACHE_SCHEMA}.{cohort_table_name} USING DELTA AS "
        "SELECT 1 AS cohort_definition_id, t.subject_id, t.first_date AS cohort_start_date, "
        "DATE_ADD(t.first_date, 365) AS cohort_end_date FROM ("
        f"SELECT e.subject_id, MIN(e.era_start) AS first_date FROM {CACHE_SCHEMA}.era_feature_presence e "
        f"WHERE e.feature_key = '{t2dm_key}' GROUP BY e.subject_id) t "
        "WHERE t.first_date >= DATE'2008-01-01' AND t.first_date <= DATE'2009-12-31'"
    )
    cohort = load_cohort(spark_backend.table(cohort_table_name, CACHE_SCHEMA), cohort_id=1)
    observation_period = spark_backend.table("observation_period", cdm_schema)
    windows = [CohortEraSpec(-365, 0), CohortEraSpec(-30, 0)]

    frame = spark_backend.execute(
        prevalence(
            cohort,
            windows=windows,
            backend=spark_backend,
            cache_schema=CACHE_SCHEMA,
            observation_period=observation_period,
        )
    )
    frame["name"] = frame["feature_key"].map(key_to_name)
    values = frame.set_index(["name", "window_index"])["prevalence"].to_dict()
    # The zero-fill guarantees both windows appear for both features.
    for spec in specs:
        assert (spec.name, 0) in values
        assert (spec.name, 1) in values
        # A shorter window can never have higher prevalence.
        assert values[(spec.name, 1)] <= values[(spec.name, 0)] + 1e-12
