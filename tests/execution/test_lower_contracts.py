from __future__ import annotations

import pytest

from circe.cohortdefinition import ConditionOccurrence
from circe.execution.lower.criteria import lower_criterion
from circe.execution.normalize.criteria import normalize_criterion
from circe.execution.plan.events import (
    FilterByCodeset,
    FilterByPersonEthnicity,
    FilterByPersonRace,
    StandardizeEventShape,
)
from circe.vocabulary import Concept

from tests.execution._domain_cases import domain_criteria_cases


@pytest.mark.parametrize(("source_table", "factory", "concept_id"), domain_criteria_cases())
def test_lower_contract_emits_source_and_standardization(
    source_table,
    factory,
    concept_id,
):
    criteria = factory()
    normalized = normalize_criterion(criteria)
    plan = lower_criterion(normalized, criterion_index=17)

    assert plan.source.table_name == source_table
    assert plan.criterion_type == criteria.__class__.__name__
    assert any(isinstance(step, StandardizeEventShape) for step in plan.steps)

    has_codeset_step = any(isinstance(step, FilterByCodeset) for step in plan.steps)
    assert has_codeset_step is (concept_id is not None)


def test_lower_contract_emits_person_race_and_ethnicity_steps_when_present():
    criteria = ConditionOccurrence(codeset_id=1)
    criteria.__dict__["race"] = [Concept(conceptId=8527)]
    criteria.__dict__["ethnicity"] = [Concept(conceptId=38003564)]

    plan = lower_criterion(normalize_criterion(criteria), criterion_index=18)
    assert any(isinstance(step, FilterByPersonRace) for step in plan.steps)
    assert any(isinstance(step, FilterByPersonEthnicity) for step in plan.steps)
