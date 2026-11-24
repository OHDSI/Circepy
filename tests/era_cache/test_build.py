from __future__ import annotations

from circe.era_cache import (
    EraCache,
    EraFeatureSpec,
    build_era_cache,
    era_feature_key,
)
from circe.era_cache.scope import cohort_scope


def _features():
    return {
        "t2dm": EraFeatureSpec(name="t2dm", source_table="condition_occurrence", concept_ids=(201826,)),
        "chf": EraFeatureSpec(name="chf", source_table="condition_occurrence", concept_ids=(316139,)),
        "hba1c": EraFeatureSpec(
            name="hba1c",
            source_table="measurement",
            concept_ids=(3004410,),
            feature_class="continuous",
        ),
        "hba1c_high": EraFeatureSpec(
            name="hba1c_high",
            source_table="measurement",
            concept_ids=(3004410,),
            feature_class="categorical",
            value_concept_ids=(4328749,),
        ),
    }


def _build(backend, specs, **kwargs):
    return build_era_cache(
        list(specs.values()),
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        **kwargs,
        scope=cohort_scope(1, cohort_table="cohort"),
    )


def _rows(backend, table):
    return backend.table(table, database="feature_cache").execute()


def test_build_writes_presence_eras(backend):
    specs = _features()
    outcome = _build(backend, specs, force=True)
    assert outcome.failed == []
    assert set(outcome.generated) == {era_feature_key(spec) for spec in specs.values()}

    t2dm = _rows(backend, "era_feature_presence")
    t2dm = t2dm[t2dm["feature_key"] == era_feature_key(specs["t2dm"])]
    assert len(t2dm) == 2
    assert set(t2dm["subject_id"]) == {1, 3}
    # Condition eras keep their end date.
    assert (t2dm["era_start"] != t2dm["era_end"]).all()


def test_build_writes_continuous_values_and_ranges(backend):
    specs = _features()
    _build(backend, specs, force=True)
    rows = _rows(backend, "era_feature_continuous")
    rows = rows[rows["feature_key"] == era_feature_key(specs["hba1c"])]
    assert len(rows) == 3
    assert set(rows["concept_id"]) == {3004410}
    assert rows["value_num"].notnull().all()
    assert rows["range_high"].notnull().all()


def test_build_writes_categorical_value_concepts(backend):
    specs = _features()
    _build(backend, specs, force=True)
    rows = _rows(backend, "era_feature_categorical")
    rows = rows[rows["feature_key"] == era_feature_key(specs["hba1c_high"])]
    assert len(rows) == 1
    assert set(rows["value_concept_id"]) == {4328749}


def test_measurement_eras_are_points(backend):
    specs = _features()
    _build(backend, specs, force=True)
    rows = _rows(backend, "era_feature_continuous")
    rows = rows[rows["feature_key"] == era_feature_key(specs["hba1c"])]
    assert (rows["era_start"] == rows["era_end"]).all()


def test_registry_records_completion(backend):
    specs = _features()
    outcome = _build(backend, specs, force=True)
    cache = EraCache(backend, schema="feature_cache")
    entries = cache.entries()
    assert set(entries) == set(outcome.generated)
    assert all(entry["completed"] for entry in entries.values())
    assert all(entry["row_count"] > 0 for entry in entries.values())
    assert cache.explain()["completed"] == len(specs)


def test_second_build_reuses_everything(backend):
    specs = _features()
    _build(backend, specs, force=True)
    outcome = _build(backend, specs)
    assert outcome.generated == []
    assert set(outcome.reused) == {era_feature_key(spec) for spec in specs.values()}
    assert outcome.failed == []


def test_force_rebuild_does_not_duplicate_rows(backend):
    specs = _features()
    _build(backend, specs, force=True)
    before = len(_rows(backend, "era_feature_presence"))
    _build(backend, specs, force=True)
    after = len(_rows(backend, "era_feature_presence"))
    assert before == after
    cache = EraCache(backend, schema="feature_cache")
    assert cache.explain()["rows"] == after + len(_rows(backend, "era_feature_continuous")) + len(
        _rows(backend, "era_feature_categorical")
    )


def test_changed_fingerprint_moves_to_a_new_generation(backend):
    specs = _features()
    first = _build(backend, specs, cdm_fingerprint="v1", force=True)
    second = _build(backend, specs, cdm_fingerprint="v2")
    assert second.reused == []
    assert set(second.generated) == set(first.generated)


def test_unknown_concept_produces_no_rows_and_is_marked_incomplete(backend):
    spec = EraFeatureSpec(name="missing", source_table="condition_occurrence", concept_ids=(999999999,))
    outcome = _build(backend, {"missing": spec}, force=True)
    assert outcome.failed
    assert outcome.failed[0]["feature_key"] == era_feature_key(spec)
    cache = EraCache(backend, schema="feature_cache")
    entry = cache.entries()[era_feature_key(spec)]
    assert entry["completed"] is False
    assert entry["row_count"] == 0


def test_descendants_expand_through_vocabulary(backend):
    # The fixture records a self-descendant relation for T2DM only.
    spec = EraFeatureSpec(
        name="t2dm_desc",
        source_table="condition_occurrence",
        concept_ids=(201826,),
        include_descendants=True,
    )
    outcome = _build(backend, {"t2dm_desc": spec}, force=True)
    assert outcome.failed == []
    assert outcome.row_counts[era_feature_key(spec)] == 2


def test_excluded_concepts_are_removed(backend):
    from circe.vocabulary import Concept, ConceptSetExpression, ConceptSetItem

    expression = ConceptSetExpression(
        items=[
            ConceptSetItem(concept=Concept(concept_id=201826)),
            ConceptSetItem(concept=Concept(concept_id=316139), is_excluded=True),
        ]
    )
    spec = EraFeatureSpec(
        name="t2dm_or_chf_except_chf",
        source_table="condition_occurrence",
        concept_set=expression,
    )
    outcome = _build(backend, {"mixed": spec}, force=True)
    assert outcome.failed == []
    rows = _rows(backend, "era_feature_presence")
    rows = rows[rows["feature_key"] == era_feature_key(spec)]
    assert set(rows["concept_id"]) == {201826}
