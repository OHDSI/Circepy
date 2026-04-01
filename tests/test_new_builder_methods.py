"""Quick smoke test for new exclude_* and at_least_of/at_most_of methods."""

from circe.cohort_builder.query_builder import CriteriaGroupBuilder, GroupConfig
from circe.evaluation.builder import EvaluationBuilder


def test_exclude_condition_on_rule_builder():
    with EvaluationBuilder("Test") as ev:
        cs = ev.concept_set("Test", 12345)
        with ev.rule("Exclusion", weight=-5) as rule:
            rule.exclude_condition(cs, anytime_before=True)
    rubric = ev.rubric
    assert len(rubric.rules) == 1
    crit = rubric.rules[0].expression.criteria_list[0]
    assert crit.occurrence.count == 0
    assert crit.occurrence.type == 0  # exactly


def test_exclude_drug_on_rule_builder():
    with EvaluationBuilder("Test") as ev:
        cs = ev.concept_set("Drug", 99999)
        with ev.rule("No Drug", weight=-3) as rule:
            rule.exclude_drug(cs, within_days_before=365)
    rubric = ev.rubric
    assert len(rubric.rules[0].expression.criteria_list) == 1
    crit = rubric.rules[0].expression.criteria_list[0]
    assert crit.occurrence.count == 0


def test_at_least_of_on_rule_builder():
    with EvaluationBuilder("Test") as ev:
        cs1 = ev.concept_set("A", 1)
        cs2 = ev.concept_set("B", 2)
        cs3 = ev.concept_set("C", 3)
        with ev.rule("2 of 3", weight=8) as rule, rule.at_least_of(2) as group:
            group.condition(cs1)
            group.drug(cs2)
            group.measurement(cs3)
    rubric = ev.rubric
    assert len(rubric.rules[0].expression.groups) == 1
    grp = rubric.rules[0].expression.groups[0]
    assert grp.type == "AT_LEAST"
    assert grp.count == 2
    assert len(grp.criteria_list) == 3


def test_at_most_of_on_rule_builder():
    with EvaluationBuilder("Test") as ev:
        cs1 = ev.concept_set("A", 1)
        cs2 = ev.concept_set("B", 2)
        with ev.rule("At Most 1", weight=-3) as rule, rule.at_most_of(1) as group:
            group.condition(cs1)
            group.condition(cs2)
    rubric = ev.rubric
    grp = rubric.rules[0].expression.groups[0]
    assert grp.type == "AT_MOST"
    assert grp.count == 1


def test_criteria_group_builder_at_least_alias():
    """at_least on CriteriaGroupBuilder should work as alias for at_least_of."""
    group = GroupConfig(type="ALL")
    builder = CriteriaGroupBuilder(None, group)
    nested = builder.at_least(2)
    assert isinstance(nested, CriteriaGroupBuilder)
    # Should have created a nested group
    assert len(group.criteria) == 1
    nested_group = group.criteria[0]
    assert isinstance(nested_group, GroupConfig)
    assert nested_group.type == "AT_LEAST"
    assert nested_group.count == 2


def test_criteria_group_builder_at_most():
    """at_most on CriteriaGroupBuilder should create a nested AT_MOST group."""
    group = GroupConfig(type="ALL")
    builder = CriteriaGroupBuilder(None, group)
    nested = builder.at_most(1)
    assert isinstance(nested, CriteriaGroupBuilder)
    nested_group = group.criteria[0]
    assert isinstance(nested_group, GroupConfig)
    assert nested_group.type == "AT_MOST"
    assert nested_group.count == 1


def test_criteria_group_builder_exclude_methods():
    """CriteriaGroupBuilder should have exclude_* methods for all key domains."""
    group = GroupConfig(type="ALL")
    builder = CriteriaGroupBuilder(None, group)
    builder.exclude_condition(1, anytime_before=True)
    builder.exclude_drug(2, within_days_before=30)
    builder.exclude_measurement(3, anytime_after=True)
    builder.exclude_procedure(4, same_day=True)
    assert len(group.criteria) == 4
