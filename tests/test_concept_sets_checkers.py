import unittest

from circe.check.checkers.concept_set_selection_checker_factory import ConceptSetSelectionCheckerFactory
from circe.check.checkers.unused_concepts_check import UnusedConceptsCheck
from circe.cohortdefinition.cohort import CohortExpression
from circe.cohortdefinition.core import ConceptSetSelection, CustomEraStrategy
from circe.cohortdefinition.criteria import (
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    PrimaryCriteria,
    VisitDetail,
)
from circe.vocabulary.concept import ConceptSet


class DummyReporter:
    def __init__(self):
        self.warnings = []

    def __call__(self, template: str, *args):
        self.warnings.append((template, args))


class TestUnusedConceptsCheck(unittest.TestCase):
    def setUp(self):
        self.checker = UnusedConceptsCheck()
        self.reporter = DummyReporter()

    def test_unused_concept_set(self):
        # ConceptSet that is not used anywhere
        concept_set = ConceptSet(id=1, name="Unused")
        expression = CohortExpression(
            concept_sets=[concept_set], primary_criteria=PrimaryCriteria(criteria_list=[])
        )
        # Use underlying check method
        self.checker._check(expression, self.reporter)
        self.assertEqual(len(self.reporter.warnings), 1)
        self.assertEqual(self.reporter.warnings[0][1][0], concept_set)

    def test_used_concept_set_in_primary_criteria(self):
        concept_set = ConceptSet(id=1, name="Used")
        expression = CohortExpression(
            concept_sets=[concept_set],
            primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        )
        self.checker._check(expression, self.reporter)
        self.assertEqual(len(self.reporter.warnings), 0)

    def test_used_in_correlated_criteria(self):
        concept_set = ConceptSet(id=1, name="Used in Correlation")
        expression = CohortExpression(
            concept_sets=[concept_set],
            primary_criteria=PrimaryCriteria(criteria_list=[]),
            additional_criteria=CriteriaGroup(
                type="ALL", criteria_list=[CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=1))]
            ),
        )
        self.checker._check(expression, self.reporter)
        self.assertEqual(len(self.reporter.warnings), 0)

    def test_used_in_nested_groups(self):
        concept_set = ConceptSet(id=1, name="Used in Nested")
        expression = CohortExpression(
            concept_sets=[concept_set],
            primary_criteria=PrimaryCriteria(criteria_list=[]),
            additional_criteria=CriteriaGroup(
                type="ALL",
                groups=[
                    CriteriaGroup(
                        type="ANY",
                        criteria_list=[CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=1))],
                    )
                ],
            ),
        )
        self.checker._check(expression, self.reporter)
        self.assertEqual(len(self.reporter.warnings), 0)

    def test_used_in_end_strategy(self):
        concept_set = ConceptSet(id=1, name="Used in Era")
        expression = CohortExpression(
            concept_sets=[concept_set], end_strategy=CustomEraStrategy(drug_codeset_id=1)
        )
        self.checker._check(expression, self.reporter)
        self.assertEqual(len(self.reporter.warnings), 0)

    def test_used_in_inclusion_rules(self):
        from circe.cohortdefinition.cohort import InclusionRule

        concept_set = ConceptSet(id=1, name="Used in Inclusion Rule")
        expression = CohortExpression(
            concept_sets=[concept_set],
            inclusion_rules=[
                InclusionRule(
                    name="Rule 1",
                    expression=CriteriaGroup(
                        type="ALL",
                        criteria_list=[CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=1))],
                    ),
                )
            ],
        )
        self.checker._check(expression, self.reporter)
        self.assertEqual(len(self.reporter.warnings), 0)

    def test_used_in_censoring_criteria(self):
        concept_set = ConceptSet(id=1, name="Used in Censoring")
        expression = CohortExpression(
            concept_sets=[concept_set], censoring_criteria=[ConditionOccurrence(codeset_id=1)]
        )
        self.checker._check(expression, self.reporter)
        self.assertEqual(len(self.reporter.warnings), 0)

    def test_completely_unused_and_not_in_any_list(self):
        concept_set = ConceptSet(id=1, name="Unused")
        expression = CohortExpression(
            concept_sets=[concept_set],
            primary_criteria=PrimaryCriteria(criteria_list=[]),
            additional_criteria=CriteriaGroup(type="ALL", criteria_list=[], groups=[]),
            inclusion_rules=[],
            censoring_criteria=[],
        )
        self.checker._check(expression, self.reporter)
        self.assertEqual(len(self.reporter.warnings), 1)

    def test_used_in_criteria_group_groups_only(self):
        concept_set = ConceptSet(id=1, name="Used Group Only")
        expression = CohortExpression(
            concept_sets=[concept_set],
            primary_criteria=PrimaryCriteria(criteria_list=[]),
            additional_criteria=CriteriaGroup(
                type="ALL",
                groups=[
                    CriteriaGroup(
                        type="ANY",
                        criteria_list=[CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=1))],
                    )
                ],
            ),
        )
        self.checker._check(expression, self.reporter)
        self.assertEqual(len(self.reporter.warnings), 0)

    def test_used_in_correlated_criteria_groups(self):
        concept_set = ConceptSet(id=1, name="Used Correlated Groups")
        expression = CohortExpression(
            concept_sets=[concept_set],
            primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=999)]),
            additional_criteria=CriteriaGroup(
                type="ALL",
                criteria_list=[
                    CorelatedCriteria(
                        criteria=ConditionOccurrence(
                            codeset_id=999,
                            correlated_criteria=CriteriaGroup(
                                type="ANY",
                                groups=[
                                    CriteriaGroup(
                                        type="ALL",
                                        criteria_list=[
                                            CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=1))
                                        ],
                                    )
                                ],
                            ),
                        )
                    )
                ],
            ),
        )
        self.checker._check(expression, self.reporter)
        self.assertEqual(len(self.reporter.warnings), 0)


class TestConceptSetSelectionCheckerFactory(unittest.TestCase):
    def test_warning_on_empty_codeset_id(self):
        reporter = DummyReporter()
        factory = ConceptSetSelectionCheckerFactory.get_factory(reporter, "TestGroup")

        visit_detail = VisitDetail(
            visit_detail_type_cs=ConceptSetSelection(codeset_id=None),
            gender_cs=ConceptSetSelection(codeset_id=123),
        )

        checker = factory._get_check_criteria(visit_detail)
        checker(visit_detail)

        # Should raise warning for visit_detail_type_cs but not gender_cs
        self.assertEqual(len(reporter.warnings), 1)
        self.assertEqual(reporter.warnings[0][1][2], "visit detail type")


if __name__ == "__main__":
    unittest.main()
