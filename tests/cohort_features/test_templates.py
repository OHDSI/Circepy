from __future__ import annotations

from circe.cohort_features import (
    CohortTemplate,
    FeatureTemplate,
    cohort_to_feature,
    expand_templates,
    template_feature_set,
)
from circe.decomposition.operators import AddInclusionRule, RequireAtEntry

from .helpers import concept_set, condition_cohort, drug_criteria_group


def _base_with_drug_concept_set():
    base = condition_cohort(201826, "T2DM")
    base.concept_sets = [*base.concept_sets, concept_set(1503297, 2)]
    return base


def test_template_flatten_applies_refinements_without_mutating_base():
    base = _base_with_drug_concept_set()
    template = CohortTemplate(
        name="T2DM plus metformin",
        base=base,
        refinements=(RequireAtEntry(drug_criteria_group(codeset_id=2)),),
    )
    flattened = template.flatten()
    assert flattened.additional_criteria is not None
    assert base.additional_criteria is None
    assert flattened.checksum() != base.checksum()


def test_template_decompose_and_variant():
    base = _base_with_drug_concept_set()
    template = CohortTemplate(name="base", base=base)
    variant = template.variant(
        "with drug",
        RequireAtEntry(drug_criteria_group(codeset_id=2)),
    )
    assert template.describe() == "base"
    assert "RequireAtEntry" in variant.describe()
    decomposed_base, refinements = variant.decompose()
    assert decomposed_base.checksum() == base.checksum()
    assert len(refinements) == 1
    assert variant.flatten().additional_criteria is not None


def test_template_to_feature_and_expand():
    base = _base_with_drug_concept_set()
    template = CohortTemplate(
        name="T2DM plus metformin",
        base=base,
        refinements=(RequireAtEntry(drug_criteria_group(codeset_id=2)),),
    )
    feature = template.to_feature(feature_id=5, name="T2DM + metformin")
    assert feature.feature_id == 5
    assert feature.name == "T2DM + metformin"
    assert feature.cohort.additional_criteria is not None

    feature_set = expand_templates([template], start_id=3)
    assert len(feature_set) == 1
    assert feature_set.features[0].feature_id == 3


def test_feature_template_refines_an_existing_feature():
    base_feature = cohort_to_feature(_base_with_drug_concept_set(), feature_id=1)
    template = FeatureTemplate(
        name="with drug",
        base=base_feature,
        refinements=(RequireAtEntry(drug_criteria_group(codeset_id=2)),),
    )
    built = template.build(feature_id=4, name="refined")
    assert built.feature_id == 4
    assert built.name == "refined"
    assert built.cohort.additional_criteria is not None
    assert base_feature.cohort.additional_criteria is None

    feature_set = template_feature_set([template], start_id=2)
    assert len(feature_set) == 1
    assert feature_set.features[0].feature_id == 2


def test_add_inclusion_rule_template():
    base = _base_with_drug_concept_set()
    rule = AddInclusionRule(
        rule=__import__("circe.cohortdefinition", fromlist=["InclusionRule"]).InclusionRule(
            name="drug",
            expression=drug_criteria_group(codeset_id=2),
        )
    )
    template = CohortTemplate(name="with rule", base=base, refinements=(rule,))
    flattened = template.flatten()
    assert len(flattened.inclusion_rules) == 1
    assert flattened.inclusion_rules[0].name == "drug"
    assert base.inclusion_rules == []
