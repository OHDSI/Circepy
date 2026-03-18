import unittest

from circe.check.checkers.comparisons import Comparisons
from circe.cohortdefinition.core import (
    DateRange,
    NumericRange,
    ObservationFilter,
    Period,
    Window,
    WindowBound,
)
from circe.cohortdefinition.criteria import (
    ConditionEra,
    ConditionOccurrence,
    Death,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
    Measurement,
    Observation,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
    VisitOccurrence,
)


class TestComparisonsCoverage(unittest.TestCase):
    # --- start_is_greater_than_end ---

    def test_start_is_greater_than_end_none(self):
        self.assertFalse(Comparisons.start_is_greater_than_end(None))

    def test_start_is_greater_than_end_numeric_incomplete(self):
        self.assertFalse(Comparisons.start_is_greater_than_end(NumericRange(value=10)))
        self.assertFalse(Comparisons.start_is_greater_than_end(NumericRange(extent=10)))
        self.assertFalse(Comparisons.start_is_greater_than_end(NumericRange()))

    def test_start_is_greater_than_end_date_incomplete(self):
        self.assertFalse(Comparisons.start_is_greater_than_end(DateRange(value="2020-01-01")))
        self.assertFalse(Comparisons.start_is_greater_than_end(DateRange(extent="2020-01-01")))
        self.assertFalse(Comparisons.start_is_greater_than_end(DateRange()))

    def test_start_is_greater_than_end_date_invalid(self):
        self.assertFalse(
            Comparisons.start_is_greater_than_end(DateRange(value="invalid", extent="2020-01-01"))
        )
        self.assertFalse(
            Comparisons.start_is_greater_than_end(DateRange(value="2020-01-01", extent="invalid"))
        )

    def test_start_is_greater_than_end_period_incomplete(self):
        self.assertFalse(Comparisons.start_is_greater_than_end(Period(start_date="2020-01-01")))
        self.assertFalse(Comparisons.start_is_greater_than_end(Period(end_date="2020-01-01")))
        self.assertFalse(Comparisons.start_is_greater_than_end(Period()))

    def test_start_is_greater_than_end_period_invalid(self):
        self.assertFalse(
            Comparisons.start_is_greater_than_end(Period(start_date="invalid", end_date="2020-01-01"))
        )
        self.assertFalse(
            Comparisons.start_is_greater_than_end(Period(start_date="2020-01-01", end_date="invalid"))
        )

    def test_start_is_greater_than_end_period_valid(self):
        self.assertTrue(
            Comparisons.start_is_greater_than_end(Period(start_date="2020-01-02", end_date="2020-01-01"))
        )
        self.assertFalse(
            Comparisons.start_is_greater_than_end(Period(start_date="2020-01-01", end_date="2020-01-02"))
        )

    def test_start_is_greater_than_end_numeric_valid(self):
        self.assertTrue(Comparisons.start_is_greater_than_end(NumericRange(value=10, extent=5)))
        self.assertFalse(Comparisons.start_is_greater_than_end(NumericRange(value=5, extent=10)))

    def test_start_is_greater_than_end_date_valid(self):
        self.assertTrue(
            Comparisons.start_is_greater_than_end(DateRange(value="2020-01-02", extent="2020-01-01"))
        )
        self.assertFalse(
            Comparisons.start_is_greater_than_end(DateRange(value="2020-01-01", extent="2020-01-02"))
        )

    def test_start_is_greater_than_end_other_type(self):
        self.assertFalse(Comparisons.start_is_greater_than_end("Not a range"))

    # --- is_date_valid ---

    def test_is_date_valid_none(self):
        self.assertFalse(Comparisons.is_date_valid(None))

    def test_is_date_valid_invalid_type(self):
        self.assertFalse(Comparisons.is_date_valid(123))

    def test_is_date_valid_string(self):
        self.assertTrue(Comparisons.is_date_valid("2020-01-01"))
        self.assertFalse(Comparisons.is_date_valid("not-a-date"))

    # --- is_start_negative ---

    def test_is_start_negative_none(self):
        self.assertFalse(Comparisons.is_start_negative(None))

    def test_is_start_negative_numeric_no_value(self):
        self.assertFalse(Comparisons.is_start_negative(NumericRange()))

    def test_is_start_negative_numeric_valid(self):
        self.assertTrue(Comparisons.is_start_negative(NumericRange(value=-1)))
        self.assertFalse(Comparisons.is_start_negative(NumericRange(value=0)))
        self.assertFalse(Comparisons.is_start_negative(NumericRange(value=1)))

    # --- compare_to ---

    def test_compare_to_none(self):
        self.assertEqual(Comparisons.compare_to(None, Window()), 0)
        self.assertEqual(Comparisons.compare_to(ObservationFilter(priorDays=0, postDays=0), None), 0)

    def test_compare_to_calculation(self):
        # range1 = prior + post = 10 + 20 = 30
        f = ObservationFilter(priorDays=10, postDays=20)

        # range2_start = coeff * days = -1 * 5 = -5
        # range2_end = coeff * days = 1 * 5 = 5
        # range2_diff = 5 - (-5) = 10
        w = Window(start=WindowBound(coeff=-1, days=5), end=WindowBound(coeff=1, days=5))

        # result = 30 - 10 = 20
        self.assertEqual(Comparisons.compare_to(f, w), 20)

    def test_compare_to_partial_window(self):
        f = ObservationFilter(priorDays=10, postDays=20)  # 30
        w = Window()  # start=None, end=None -> range2_start=0, range2_end=0 -> 0

        self.assertEqual(Comparisons.compare_to(f, w), 30)

    # --- is_before / endpoints ---

    def test_is_before_none(self):
        self.assertFalse(Comparisons.is_before(None))

    def test_is_before_endpoint_none(self):
        self.assertFalse(Comparisons.is_before_endpoint(None))

    def test_is_after_endpoint_none(self):
        self.assertFalse(Comparisons.is_after_endpoint(None))

    def test_is_before_true(self):
        # start before (< 0), end not after (<= 0)
        w = Window(start=WindowBound(coeff=-1, days=1), end=WindowBound(coeff=-1, days=1))
        self.assertTrue(Comparisons.is_before(w))

    def test_is_before_false_start_not_before(self):
        w = Window(start=WindowBound(coeff=1, days=1), end=WindowBound(coeff=-1, days=1))
        self.assertFalse(Comparisons.is_before(w))

    def test_is_before_false_end_after(self):
        w = Window(start=WindowBound(coeff=-1, days=1), end=WindowBound(coeff=1, days=1))
        self.assertFalse(Comparisons.is_before(w))

    # --- compare_concept_set ---

    def test_compare_concept_set(self):
        from circe.vocabulary.concept import (
            Concept,
            ConceptSet,
            ConceptSetExpression,
            ConceptSetItem,
        )

        c1 = Concept(
            concept_code="A",
            domain_id="D",
            vocabulary_id="V",
            concept_id=1,
            concept_name="N",
            standard_concept="S",
            invalid_reason="I",
            concept_class_id="C",
        )
        c2 = Concept(
            concept_code="A",
            domain_id="D",
            vocabulary_id="V",
            concept_id=1,
            concept_name="N",
            standard_concept="S",
            invalid_reason="I",
            concept_class_id="C",
        )
        c3 = Concept(
            concept_code="B",
            domain_id="D",
            vocabulary_id="V",
            concept_id=2,
            concept_name="N2",
            standard_concept="S",
            invalid_reason="I",
            concept_class_id="C",
        )

        # Same expression object
        expr1 = ConceptSetExpression(items=[ConceptSetItem(concept=c1)])
        cs1 = ConceptSet(id=1, name="S1", expression=expr1)

        predicate = Comparisons.compare_concept_set(cs1)
        self.assertTrue(predicate(cs1))

        # Diff expression objects, same content
        expr2 = ConceptSetExpression(items=[ConceptSetItem(concept=c2)])
        cs2 = ConceptSet(id=2, name="S2", expression=expr2)
        self.assertTrue(predicate(cs2))

        # Diff content (length)
        expr3 = ConceptSetExpression(items=[ConceptSetItem(concept=c1), ConceptSetItem(concept=c3)])
        cs3 = ConceptSet(id=3, name="S3", expression=expr3)
        self.assertFalse(predicate(cs3))

        # Diff content (concept mismatch)
        expr4 = ConceptSetExpression(items=[ConceptSetItem(concept=c3)])
        cs4 = ConceptSet(id=4, name="S4", expression=expr4)
        self.assertFalse(predicate(cs4))

        # Source has no expression
        cs_empty = ConceptSet(id=5, name="S5", expression=None)
        predicate_empty = Comparisons.compare_concept_set(cs_empty)
        # Assuming implementation detailed behavior: if source.expression is None, only exact match or both None works?
        # Looking at code: if concept_set.expression == source.expression (None == None) -> True.
        self.assertTrue(predicate_empty(cs_empty))

        # Target has no expression
        self.assertFalse(predicate(cs_empty))

    # --- compare_criteria ---

    def test_compare_criteria_diff_types(self):
        self.assertFalse(Comparisons.compare_criteria(ConditionEra(), DrugEra()))

    def test_compare_criteria_all_types(self):
        # Create instances of all criteria types with matching and non-matching codeset_ids
        types = [
            ConditionEra,
            ConditionOccurrence,
            Death,
            DeviceExposure,
            DoseEra,
            DrugEra,
            DrugExposure,
            Measurement,
            Observation,
            ProcedureOccurrence,
            Specimen,
            VisitOccurrence,
            VisitDetail,
        ]

        for cls in types:
            c1 = cls(codeset_id=1)
            c2 = cls(codeset_id=1)
            c3 = cls(codeset_id=2)

            self.assertTrue(Comparisons.compare_criteria(c1, c2), f"Failed for {cls.__name__} match")
            self.assertFalse(
                Comparisons.compare_criteria(c1, c3),
                f"Failed for {cls.__name__} mismatch",
            )

    def test_compare_criteria_unknown_type(self):
        class UnknownCriteria:
            pass

        self.assertFalse(Comparisons.compare_criteria(UnknownCriteria(), UnknownCriteria()))
