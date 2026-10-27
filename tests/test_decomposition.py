"""Tests for the decomposable-cohort algebra (bases + v1-placed refinements)."""

from __future__ import annotations

import pytest

from circe.cohort_definition_set import CohortDefinitionSet
from circe.cohortdefinition import (
    CohortExpression,
    CollapseSettings,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    DateOffsetStrategy,
    InclusionRule,
    Period,
    PrimaryCriteria,
    ResultLimit,
)
from circe.decomposition import (
    AddCensoring,
    AddConceptSets,
    AddInclusionRule,
    RequireAtEntry,
    SetCensorWindow,
    SetCollapse,
    SetEndStrategy,
    SetExpressionLimit,
    SetQualifiedLimit,
    SetTitle,
    decompose_cohort_set,
    semantic_expression_key,
)
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _concept_set(set_id: int, concept_id: int, name: str | None = None) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        name=name,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def _rule(name: str, set_id: int) -> InclusionRule:
    return InclusionRule(
        name=name,
        expression=CriteriaGroup(
            type="ALL",
            criteria_list=[CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=set_id))],
        ),
    )


def _group(set_id: int, mode: str = "ALL") -> CriteriaGroup:
    return CriteriaGroup(
        type=mode,
        criteria_list=[CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=set_id))],
    )


def _expression(
    *,
    concept_sets: list[ConceptSet] | None = None,
    primary_codeset_id: int = 1,
    additional: CriteriaGroup | None = None,
    rules: list[InclusionRule] | None = None,
    qualified_limit: ResultLimit | None = None,
    expression_limit: ResultLimit | None = None,
    end_strategy=None,
    censoring: list | None = None,
    censor_window: Period | None = None,
    collapse: CollapseSettings | None = None,
    title: str | None = None,
) -> CohortExpression:
    return CohortExpression(
        concept_sets=concept_sets
        if concept_sets is not None
        else [_concept_set(1, 111), _concept_set(2, 222), _concept_set(3, 333)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=primary_codeset_id)]),
        additional_criteria=additional,
        inclusion_rules=rules or [],
        qualified_limit=qualified_limit,
        expression_limit=expression_limit,
        end_strategy=end_strategy,
        censoring_criteria=censoring or [],
        censor_window=censor_window,
        collapse_settings=collapse,
        title=title,
    )


def _cohort_set(*cohorts: tuple[int, str, CohortExpression]) -> CohortDefinitionSet:
    cohort_set = CohortDefinitionSet()
    for cohort_id, name, expression in cohorts:
        cohort_set.add(cohort_id=cohort_id, cohort_name=name, expression=expression)
    return cohort_set


def _dump(expression: CohortExpression) -> dict:
    return expression.model_dump(by_alias=True, mode="json", exclude_none=True)


# ---------------------------------------------------------------------------
# Structure and flattening
# ---------------------------------------------------------------------------


def test_decompose_detects_inclusion_rule_refinement():
    base = _expression()
    derived = _expression(rules=[_rule("r222", 2)])
    decomposition = decompose_cohort_set(_cohort_set((1, "base", base), (2, "derived", derived)))

    assert list(decomposition.bases) == [1]
    assert list(decomposition.derived) == [2]
    node = decomposition.derived[2]
    assert node.base_id == 1
    assert node.parent_id == 1
    assert [refinement.kind for refinement in node.refinements] == ["add_inclusion_rule"]
    assert decomposition.verify() == []
    assert _dump(decomposition.flatten(2)) == _dump(derived)


def test_decompose_detects_chain_of_refinements():
    c1 = _expression()
    c2 = _expression(rules=[_rule("r222", 2)])
    c3 = _expression(rules=[_rule("r222", 2), _rule("r333", 3)])
    decomposition = decompose_cohort_set(_cohort_set((1, "a", c1), (2, "b", c2), (3, "c", c3)))

    assert list(decomposition.bases) == [1]
    assert set(decomposition.derived) == {2, 3}
    assert decomposition.derived[3].base_id == 1
    assert [refinement.kind for refinement in decomposition.derived[3].refinements] == [
        "add_inclusion_rule",
        "add_inclusion_rule",
    ]
    assert _dump(decomposition.flatten(3)) == _dump(c3)
    assert decomposition.verify() == []


def test_decompose_all_operator_kinds_round_trip_byte_identically():
    base = _expression()
    derived = _expression(
        additional=_group(3),
        rules=[_rule("r222", 2)],
        qualified_limit=ResultLimit(type="first"),
        expression_limit=ResultLimit(type="last"),
        end_strategy=DateOffsetStrategy(date_field="StartDate", offset=7),
        censoring=[ConditionOccurrence(codeset_id=2)],
        censor_window=Period(start_date="2001-01-01", end_date="2019-12-31"),
        collapse=CollapseSettings(era_pad=3),
        title="all operators",
    )
    decomposition = decompose_cohort_set(_cohort_set((1, "base", base), (2, "all", derived)))

    kinds = [refinement.kind for refinement in decomposition.derived[2].refinements]
    assert kinds == [
        "set_qualified_limit",
        "require_at_entry",
        "add_inclusion_rule",
        "set_expression_limit",
        "set_end_strategy",
        "add_censoring",
        "set_censor_window",
        "set_collapse",
        "set_title",
    ]
    assert isinstance(decomposition.derived[2].refinements[0], SetQualifiedLimit)
    assert isinstance(decomposition.derived[2].refinements[1], RequireAtEntry)
    assert isinstance(decomposition.derived[2].refinements[2], AddInclusionRule)
    assert isinstance(decomposition.derived[2].refinements[3], SetExpressionLimit)
    assert isinstance(decomposition.derived[2].refinements[4], SetEndStrategy)
    assert isinstance(decomposition.derived[2].refinements[5], AddCensoring)
    assert isinstance(decomposition.derived[2].refinements[6], SetCensorWindow)
    assert isinstance(decomposition.derived[2].refinements[7], SetCollapse)
    assert isinstance(decomposition.derived[2].refinements[8], SetTitle)
    assert _dump(decomposition.flatten(2)) == _dump(derived)
    assert decomposition.explain()["all_definitions_byte_identical"] is True


def test_decompose_adds_concept_sets_used_by_refinements():
    base = _expression(concept_sets=[_concept_set(1, 111)])
    derived = _expression(
        concept_sets=[_concept_set(1, 111), _concept_set(2, 222, "new set")],
        rules=[_rule("r222", 2)],
    )
    decomposition = decompose_cohort_set(_cohort_set((1, "base", base), (2, "derived", derived)))

    kinds = [refinement.kind for refinement in decomposition.derived[2].refinements]
    assert kinds == ["add_concept_sets", "add_inclusion_rule"]
    assert isinstance(decomposition.derived[2].refinements[0], AddConceptSets)
    assert _dump(decomposition.flatten(2)) == _dump(derived)


def test_decompose_canonicalises_cohort_local_concept_set_ids():
    base = _expression(concept_sets=[_concept_set(1, 111)])
    derived = _expression(
        concept_sets=[_concept_set(7, 111), _concept_set(9, 222)],
        primary_codeset_id=7,
        rules=[_rule("r222", 9)],
    )
    decomposition = decompose_cohort_set(_cohort_set((1, "base", base), (2, "derived", derived)))

    assert list(decomposition.derived) == [2]
    flattened = decomposition.flatten(2)
    assert semantic_expression_key(flattened) == semantic_expression_key(derived)
    assert _dump(flattened) != _dump(derived)  # local ids were canonicalised
    assert decomposition.explain()["all_definitions_semantically_identical"] is True
    assert decomposition.explain()["all_definitions_byte_identical"] is False


# ---------------------------------------------------------------------------
# Conservative fallbacks
# ---------------------------------------------------------------------------


def test_decompose_keeps_unrelated_cohorts_as_bases():
    first = _expression()
    second = _expression(primary_codeset_id=2)
    third = _expression(rules=[_rule("r222", 2)])
    decomposition = decompose_cohort_set(
        _cohort_set((1, "first", first), (2, "second", second), (3, "third", third))
    )

    # 1 and 3 share a primary checkpoint; 2 does not.
    assert 2 in decomposition.bases
    assert 1 in decomposition.bases
    assert 3 in decomposition.derived
    assert decomposition.derived[3].base_id == 1


def test_decompose_rebases_instead_of_removing_rules():
    # Removing/rewriting a rule widens the definition, which is outside the
    # narrowing algebra: the simpler cohort becomes the base instead.
    parent = _expression(rules=[_rule("r222", 2)])
    fewer = _expression()
    different = _expression(rules=[_rule("r333", 3)])
    decomposition = decompose_cohort_set(
        _cohort_set((1, "parent", parent), (2, "fewer", fewer), (3, "different", different))
    )

    assert list(decomposition.bases) == [2]
    assert set(decomposition.derived) == {1, 3}
    assert _dump(decomposition.flatten(1)) == _dump(parent)
    assert _dump(decomposition.flatten(3)) == _dump(different)


def test_decompose_rejects_changed_parent_concept_set_content():
    common = _concept_set(1, 111)
    base = _expression(concept_sets=[common])
    changed = _expression(concept_sets=[_concept_set(1, 444), _concept_set(2, 222)], rules=[_rule("r222", 2)])
    decomposition = decompose_cohort_set(_cohort_set((1, "base", base), (2, "changed", changed)))

    assert not decomposition.derived


# ---------------------------------------------------------------------------
# API surface / reporting
# ---------------------------------------------------------------------------


def test_decomposition_explain_and_describe():
    base = _expression(title="base")
    derived = _expression(title="derived", rules=[_rule("r222", 2)])
    decomposition = decompose_cohort_set(_cohort_set((1, "Base", base), (2, "Derived", derived)))

    summary = decomposition.explain()
    assert summary["cohorts"] == 2
    assert summary["primary_checkpoints"] == 1
    assert summary["primary_scans_saved"] == 1
    assert summary["shared_primary_signatures"] == 1
    assert summary["bases"][0]["cohort_name"] == "Base"
    assert summary["bases"][0]["derived_count"] == 1
    assert summary["derived"][0]["refinements"][0]["operator"] in {
        "add_inclusion_rule",
        "set_title",
    }

    description = decomposition.describe()
    assert "Decomposed 2 cohort(s)" in description
    assert "Derived" in description or "derived" in description
    assert "byte-identical" in description


def test_decomposition_empty_set():
    decomposition = decompose_cohort_set(CohortDefinitionSet())

    assert len(decomposition) == 0
    assert decomposition.bases == {}
    assert decomposition.derived == {}
    assert decomposition.verify() == []
    assert decomposition.explain()["cohorts"] == 0


def test_decomposition_flatten_all_and_unknown_id():
    base = _expression(title="base")
    derived = _expression(title="derived", rules=[_rule("r222", 2)])
    decomposition = decompose_cohort_set(_cohort_set((1, "Base", base), (2, "Derived", derived)))

    flattened = decomposition.flatten_all()
    assert [cohort.cohort_id for cohort in flattened] == [1, 2]
    assert _dump(flattened[1].expression) == _dump(base)
    assert _dump(flattened[2].expression) == _dump(derived)

    with pytest.raises(KeyError):
        decomposition.flatten(999)


def test_derived_cohort_describe_includes_operators():
    base = _expression()
    derived = _expression(rules=[_rule("r222", 2)])
    decomposition = decompose_cohort_set(_cohort_set((1, "Base", base), (2, "Derived", derived)))

    text = decomposition.derived[2].describe()
    assert "base 1" in text
    assert "AddInclusionRule" in text
    assert decomposition.derived[2].depth == 1


def test_canonicalizer_reuses_content_and_ignores_display_metadata():
    from circe.decomposition import ConceptSetCanonicalizer, concept_set_content_key

    canonicalizer = ConceptSetCanonicalizer()
    first = _concept_set(1, 111, "first name")
    second = _concept_set(9, 111, "other name")

    assert concept_set_content_key(first.expression) == concept_set_content_key(second.expression)
    assert canonicalizer.register(first) == 1
    assert canonicalizer.register(second) == 1
    assert len(canonicalizer) == 1

    expression = _expression(concept_sets=[second], primary_codeset_id=9)
    canonical = canonicalizer.canonicalize(expression)
    assert [concept_set.id for concept_set in canonical.concept_sets] == [1]
    assert canonical.primary_criteria.criteria_list[0].codeset_id == 1
    # The caller's expression is never mutated.
    assert expression.concept_sets[0].id == 9


def test_semantic_key_can_ignore_title():
    from circe.decomposition import semantic_expression_key

    first = _expression(title="one")
    second = _expression(title="two")

    assert semantic_expression_key(first) != semantic_expression_key(second)
    assert semantic_expression_key(first, include_title=False) == semantic_expression_key(
        second, include_title=False
    )


def test_operator_descriptions_cover_every_refinement():
    from circe.decomposition import (
        AddCensoring,
        AddConceptSets,
        AddInclusionRule,
        RequireAtEntry,
        SetCensorWindow,
        SetCollapse,
        SetEndStrategy,
        SetExpressionLimit,
        SetQualifiedLimit,
        SetTitle,
    )

    concept_set = _concept_set(4, 444)
    operators = [
        RequireAtEntry(_group(2)),
        AddInclusionRule(_rule("r", 2)),
        SetQualifiedLimit(ResultLimit(type="first")),
        SetExpressionLimit(ResultLimit(type="last")),
        SetEndStrategy(DateOffsetStrategy(date_field="StartDate", offset=1)),
        AddCensoring(ConditionOccurrence(codeset_id=2)),
        SetCensorWindow(Period(start_date="2000-01-01", end_date="2001-01-01")),
        SetCollapse(CollapseSettings(era_pad=2)),
        AddConceptSets((concept_set,)),
        SetTitle("title"),
    ]

    for operator in operators:
        assert operator.describe()
        assert operator.to_dict()["operator"] == operator.kind
        operator.apply(_expression())
