"""Tests for cohort-scoped era-cache builds.

The default pipeline caches a study population, not the whole CDM.  These tests
pin that behaviour: a cohort-scoped build must contain rows for cohort members
only, must not be confused with a whole-CDM build, and must not be reused for a
different cohort set.
"""

from __future__ import annotations

import pytest

from circe.era_cache import EraFeatureSpec, build_era_cache
from circe.era_cache.identity import cache_key
from circe.era_cache.scope import (
    WHOLE_CDM_SCOPE,
    CohortScope,
    cohort_scope,
    scope_from_cohort_table,
    whole_cdm,
)


def _t2dm() -> EraFeatureSpec:
    return EraFeatureSpec(
        name="t2dm",
        source_table="condition_occurrence",
        concept_ids=(201826,),
    )


def _cache_key_for(scope) -> str:
    return cache_key(cdm_schema="main", vocabulary_schema="main", scope_fingerprint=scope.fingerprint())


def _cached_subjects(backend) -> set[int]:
    table = backend.table("era_feature_presence", database="feature_cache")
    return set(table.select("subject_id").execute()["subject_id"].tolist())


# -- scope object ----------------------------------------------------------


def test_cohort_scope_requires_a_table():
    with pytest.raises(ValueError, match="needs a cohort_table"):
        cohort_scope(1)


def test_cohort_scope_requires_cohort_ids():
    with pytest.raises(ValueError, match="at least one cohort id"):
        CohortScope(kind="cohort", cohort_table="cohort")


def test_cohort_scope_rejects_empty_ids():
    with pytest.raises(ValueError, match="at least one cohort id"):
        cohort_scope([])


def test_scope_from_cohort_table_covers_every_cohort():
    scope = scope_from_cohort_table("cohort")

    assert scope.all_cohorts is True
    assert scope.cohort_ids == ()


def test_whole_cdm_and_cohort_scopes_are_distinct():
    assert whole_cdm().is_whole_cdm is True
    assert cohort_scope(1, cohort_table="cohort").is_whole_cdm is False
    assert whole_cdm().fingerprint() != cohort_scope(1, cohort_table="cohort").fingerprint()


def test_different_cohort_ids_have_different_fingerprints():
    first = cohort_scope(1, cohort_table="cohort")
    second = cohort_scope(2, cohort_table="cohort")

    assert first.fingerprint() != second.fingerprint()


def test_fingerprint_is_order_insensitive():
    assert (
        cohort_scope([1, 2], cohort_table="cohort").fingerprint()
        == cohort_scope([2, 1], cohort_table="cohort").fingerprint()
    )


def test_describe_is_json_safe():
    described = cohort_scope(1, cohort_table="cohort", schema="res").describe()

    assert described["kind"] == "cohort"
    assert described["cohort_ids"] == [1]
    assert described["cohort_table"] == "cohort"
    assert isinstance(described["fingerprint"], str)


def test_whole_cdm_subjects_is_an_error():
    with pytest.raises(ValueError, match="no subject relation"):
        WHOLE_CDM_SCOPE.subjects(None)


# -- cache identity --------------------------------------------------------


def test_cache_key_separates_scope_generations():
    base = {"cdm_schema": "cdm", "vocabulary_schema": "vocab"}

    first = cache_key(**base, scope_fingerprint=cohort_scope(1, cohort_table="cohort").fingerprint())
    second = cache_key(**base, scope_fingerprint=cohort_scope(2, cohort_table="cohort").fingerprint())
    whole = cache_key(**base, scope_fingerprint=whole_cdm().fingerprint())

    assert len({first, second, whole}) == 3


# -- build behaviour -------------------------------------------------------


def test_build_requires_an_explicit_scope(backend):
    with pytest.raises(ValueError, match="requires an explicit scope"):
        build_era_cache(
            [_t2dm()],
            backend=backend,
            cache_schema="feature_cache",
            cdm_schema="main",
        )


def test_cohort_scoped_build_only_caches_cohort_members(backend):
    """The fixture cohort 1 contains people 1-4 but not 5."""
    build_era_cache(
        [_t2dm()],
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        scope=cohort_scope(1, cohort_table="cohort"),
    )

    subjects = _cached_subjects(backend)
    assert subjects
    assert subjects <= {1, 2, 3, 4}


def test_cohort_scope_restricts_to_the_named_cohort(backend):
    """Cohort 2 holds a different member; only that member may be cached."""
    backend.raw_sql("DROP TABLE IF EXISTS cohort")
    backend.raw_sql(
        "CREATE TABLE cohort (cohort_definition_id INT, subject_id INT, "
        "cohort_start_date DATE, cohort_end_date DATE)"
    )
    backend.raw_sql(
        "INSERT INTO cohort VALUES (1, 1, DATE '2020-08-01', DATE '2021-08-01'), "
        "(2, 2, DATE '2020-08-01', DATE '2021-08-01')"
    )

    build_era_cache(
        [_t2dm()],
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        scope=cohort_scope(1, cohort_table="cohort"),
    )

    assert _cached_subjects(backend) <= {1}


def test_changing_the_cohort_scope_invalidates_reuse(backend):
    """A build scoped to one member must not be reused for a different member."""
    backend.raw_sql("DROP TABLE IF EXISTS cohort")
    backend.raw_sql(
        "CREATE TABLE cohort (cohort_definition_id INT, subject_id INT, "
        "cohort_start_date DATE, cohort_end_date DATE)"
    )
    backend.raw_sql(
        "INSERT INTO cohort VALUES (1, 1, DATE '2020-08-01', DATE '2021-08-01'), "
        "(2, 3, DATE '2020-08-01', DATE '2021-08-01')"
    )

    first = build_era_cache(
        [_t2dm()],
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        scope=cohort_scope(1, cohort_table="cohort"),
    )
    assert first.generated
    assert _cached_subjects(backend) <= {1}

    second = build_era_cache(
        [_t2dm()],
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        scope=cohort_scope(2, cohort_table="cohort"),
    )

    # Different scope fingerprint -> different generation -> regenerated, not
    # reused. Both generations coexist by design (old rows are only removed on
    # an explicit purge), so assert on the second generation's own rows.
    assert second.generated
    assert not second.reused

    table = backend.table("era_feature_presence", database="feature_cache")
    second_generation = table.filter(
        table.cache_key == _cache_key_for(cohort_scope(2, cohort_table="cohort"))
    )
    assert set(second_generation.select("subject_id").execute()["subject_id"]) == {3}


def test_repeated_build_with_the_same_scope_is_reused(backend):
    scope = cohort_scope(1, cohort_table="cohort")
    build_era_cache(
        [_t2dm()],
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        scope=scope,
    )

    again = build_era_cache(
        [_t2dm()],
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        scope=cohort_scope(1, cohort_table="cohort"),
    )

    assert again.reused
    assert not again.generated


def test_whole_cdm_build_is_opt_in_and_separate(backend):
    """whole_cdm() still works, and lives in its own generation."""
    outcome = build_era_cache(
        [_t2dm()],
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        scope=whole_cdm(),
    )

    assert outcome.generated
    # A whole-CDM build must not reuse a cohort-scoped row and vice versa.
    scoped = build_era_cache(
        [_t2dm()],
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        scope=cohort_scope(1, cohort_table="cohort"),
    )
    assert scoped.generated
