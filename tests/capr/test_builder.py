"""Unit tests for circe.capr concept sets and builder behaviour.

Capr-compatible concept-set ids are pinned to values produced by R's
``digest::digest()``; they are the load-bearing part of the port, so they are
asserted literally rather than recomputed.
"""

from __future__ import annotations

import json

import pytest

from circe import capr
from circe.capr import CaprConceptSet, cs, descendants, exclude, mapped


def t2dm() -> CaprConceptSet:
    return cs(descendants(201826), name="T2DM")


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (lambda: cs(descendants(201826), name="T2DM"), "124d04652b638f0065b3eefe76cc5793"),
        (lambda: cs(201826, 201254, name="Diabetes"), "00e45360499d6128e105bf47f2cb0e18"),
        (lambda: cs(exclude(4256051), name="x"), "a03be68df2cbc8e30fed959ef95089c6"),
        (lambda: cs(mapped(1), name="y"), "010a0b1fba32e252e206acad2e7175f9"),
        (
            lambda: cs(exclude(descendants(mapped(5))), name="z"),
            "3dadec77e9844588e837b4c8245088be",
        ),
        (lambda: cs(name="e"), "2f88e16c4f21bfcb290b2a8288c05bd0"),
    ],
)
def test_concept_set_id_matches_r_capr(factory, expected):
    assert factory().id == expected


def test_concept_set_id_ignores_item_order():
    assert cs(201826, 201254, name="a").id == cs(201254, 201826, name="b").id


def test_concept_set_id_ignores_name():
    assert cs(descendants(201826), name="one").id == cs(descendants(201826), name="two").id


def test_exclude_does_not_imply_descendants():
    item = cs(exclude(4256051), name="x").items[0]
    assert item.is_excluded is True
    assert item.include_descendants is False
    assert item.include_mapped is False


def test_nested_helpers_compose():
    item = cs(exclude(descendants(mapped(5))), name="z").items[0]
    assert item.is_excluded and item.include_descendants and item.include_mapped


def test_negative_concept_id_rejected():
    with pytest.raises(ValueError, match="exclude"):
        cs(-4256051, name="neg")


def test_duplicate_concepts_warn():
    with pytest.warns(UserWarning, match="duplicated"):
        cs(201826, 201826, name="dupes")


def test_booleans_rejected():
    with pytest.raises(TypeError):
        cs(True, name="bad")


# --- builder behaviour ------------------------------------------------------


def _minimal_cohort():
    return capr.cohort(
        entry=capr.entry(capr.condition_occurrence(t2dm()), primary_criteria_limit="First"),
        attrition=capr.attrition(expression_limit="First"),
        exit=capr.exit(capr.observation_exit()),
    )


def test_to_cohort_expression_returns_model():
    from circe.cohortdefinition import CohortExpression

    assert isinstance(capr.to_cohort_expression(_minimal_cohort()), CohortExpression)


def test_cohort_expression_round_trips_through_json():
    """A compiled cohort survives JSON -> CohortExpression unchanged semantically.

    The shared models add ``False`` defaults on round-trip (e.g. ``First``), so
    the comparison ignores false-valued keys rather than requiring byte equality.
    """
    from circe.api import cohort_expression_from_json

    def strip_false(node):
        if isinstance(node, dict):
            return {k: strip_false(v) for k, v in node.items() if v is not False and k != "cdmVersionRange"}
        if isinstance(node, list):
            return [strip_false(v) for v in node]
        return node

    expression = capr.to_cohort_expression(_minimal_cohort())
    reparsed = cohort_expression_from_json(expression.model_dump_json())
    assert strip_false(reparsed.model_dump()) == strip_false(expression.model_dump())


def test_concept_sets_numbered_from_zero():
    hf = cs(descendants(316139), name="HF")
    rule = capr.with_all(capr.at_least(1, capr.condition_occurrence(hf)))
    cd = capr.cohort(
        entry=capr.entry(capr.condition_occurrence(t2dm())),
        attrition=capr.attrition(**{"hf": rule}, expression_limit="First"),
    )
    payload = json.loads(capr.to_cohort_json(cd))
    assert [c["id"] for c in payload["ConceptSets"]] == [0, 1]
    assert payload["PrimaryCriteria"]["CriteriaList"][0]["ConditionOccurrence"]["CodesetId"] == 0


def test_cohort_accepts_bare_query():
    cd = capr.cohort(capr.condition_occurrence(t2dm()))
    assert isinstance(cd.entry, capr.CohortEntry)
    assert len(json.loads(capr.to_cohort_json(cd))["PrimaryCriteria"]["CriteriaList"]) == 1


def test_cohort_with_shadowed_entry_variable():
    entry = "shadows the function in R"  # noqa: F841 - the point of the test
    cd = capr.cohort(capr.condition_occurrence(t2dm()))
    assert isinstance(cd.entry, capr.CohortEntry)


def test_entry_rejects_criteria():
    criterion = capr.at_least(1, capr.condition_occurrence(t2dm()))
    with pytest.raises(capr.CaprError, match="only accepts queries"):
        capr.entry(criterion)


def test_attrition_rejects_bare_criterion():
    criterion = capr.at_least(1, capr.condition_occurrence(t2dm()))
    with pytest.raises(capr.CaprError, match="must be a group"):
        capr.attrition(**{"bare": criterion})


def test_query_requires_concept_set():
    with pytest.raises(capr.CaprError, match="requires a concept set"):
        capr.condition_occurrence()


def test_death_needs_no_concept_set():
    assert isinstance(capr.death(), capr.criteria._Query)


def test_distinct_requires_count_column():
    with pytest.raises(capr.CaprError, match="count_column"):
        capr.at_least(1, capr.condition_occurrence(t2dm()), distinct=True)


def test_validate_flags_all_with_first():
    cd = capr.cohort(
        entry=capr.entry(capr.condition_occurrence(t2dm()), primary_criteria_limit="All"),
        attrition=capr.attrition(expression_limit="First"),
    )
    assert capr.validate(cd, strict=False)
    with pytest.raises(capr.CaprError):
        capr.validate(cd)


def test_validate_passes_on_good_cohort():
    assert capr.validate(_minimal_cohort()) == []


def test_window_stores_magnitude_and_sign():
    window = capr.event_starts(-365, 0).to_window()
    assert window.start.coeff == -1 and window.start.days == 365
    assert window.end.coeff == -1 and window.end.days == 0


def test_unbounded_window_omits_days():
    window = capr.event_starts(-capr.INF, capr.INF).to_window()
    assert window.start.days is None and window.start.coeff == -1
    assert window.end.days is None and window.end.coeff == 1
