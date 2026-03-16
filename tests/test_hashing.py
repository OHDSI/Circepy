import unittest

from circe.cohortdefinition.cohort import CohortExpression
from circe.cohortdefinition.criteria import PrimaryCriteria
from circe.vocabulary.concept import (
    Concept,
    ConceptSet,
    ConceptSetExpression,
    ConceptSetItem,
)


class TestCohortHashing(unittest.TestCase):
    """Test suite for CohortExpression checksum stability and correctness."""

    def test_stability(self):
        """Test that checksums are stable for identical objects."""
        c1 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        c2 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        self.assertEqual(c1.checksum(), c2.checksum())

    def test_concept_name_agnosticism(self):
        """Test that checksums are the same even if Concept Name differs."""
        # Setup Cohort 1
        c1 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs1 = ConceptSet(id=1, name="Set 1")
        item1 = ConceptSetItem(
            concept=Concept(
                concept_id=123, concept_name="Name A", standard_concept="S"
            ),
            isExcluded=False,
        )
        cs1.expression = ConceptSetExpression(items=[item1])
        c1.concept_sets = [cs1]

        # Setup Cohort 2 (Different Concept Name, same ID)
        c2 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs2 = ConceptSet(id=1, name="Set 1")
        item2 = ConceptSetItem(
            concept=Concept(
                concept_id=123, concept_name="Name B", standard_concept="S"
            ),
            isExcluded=False,
        )
        cs2.expression = ConceptSetExpression(items=[item2])
        c2.concept_sets = [cs2]

        # Should match despite name difference
        self.assertEqual(
            c1.checksum(),
            c2.checksum(),
            "Checksum should ignore concept name differences",
        )

    def test_metadata_agnosticism(self):
        """Test that checksums ignore other metadata fields."""
        # Setup Cohort 1
        c1 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs1 = ConceptSet(id=1, name="Set 1")
        item1 = ConceptSetItem(
            concept=Concept(concept_id=123, standard_concept="S", vocabulary_id="None"),
            isExcluded=False,
        )
        cs1.expression = ConceptSetExpression(items=[item1])
        c1.concept_sets = [cs1]

        # Setup Cohort 2 (Different Standard Concept, Vocab ID)
        c2 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs2 = ConceptSet(id=1, name="Set 1")
        item2 = ConceptSetItem(
            concept=Concept(
                concept_id=123, standard_concept="C", vocabulary_id="RxNorm"
            ),
            isExcluded=False,
        )
        cs2.expression = ConceptSetExpression(items=[item2])
        c2.concept_sets = [cs2]

        self.assertEqual(
            c1.checksum(), c2.checksum(), "Checksum should ignore metadata differences"
        )

    def test_crucial_flags_sensitivity(self):
        """Test that checksums CHANGE when functional flags change."""
        # Cohort 1: Excluded = False
        c1 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs1 = ConceptSet(id=1, name="Set 1")
        item1 = ConceptSetItem(concept=Concept(concept_id=123), isExcluded=False)
        cs1.expression = ConceptSetExpression(items=[item1])
        c1.concept_sets = [cs1]

        # Cohort 2: Excluded = True
        c2 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs2 = ConceptSet(id=1, name="Set 1")
        item2 = ConceptSetItem(concept=Concept(concept_id=123), isExcluded=True)
        cs2.expression = ConceptSetExpression(items=[item2])
        c2.concept_sets = [cs2]

        self.assertNotEqual(
            c1.checksum(), c2.checksum(), "Checksum must change if isExcluded changes"
        )

    def test_deduplication(self):
        """Test that duplicate concept items are handled as the same set."""
        # Cohort 1: Single item
        c1 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs1 = ConceptSet(id=1, name="Set 1")
        item1 = ConceptSetItem(concept=Concept(concept_id=123), isExcluded=False)
        cs1.expression = ConceptSetExpression(items=[item1])
        c1.concept_sets = [cs1]

        # Cohort 2: Duplicate items (same ID, same flags)
        c2 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs2 = ConceptSet(id=1, name="Set 1")
        item2a = ConceptSetItem(concept=Concept(concept_id=123), isExcluded=False)
        item2b = ConceptSetItem(concept=Concept(concept_id=123), isExcluded=False)
        cs2.expression = ConceptSetExpression(items=[item2a, item2b])
        c2.concept_sets = [cs2]

        self.assertEqual(
            c1.checksum(),
            c2.checksum(),
            "Checksum should treat duplicate items as single item",
        )

    def test_sensitivity_to_id(self):
        """Test sensitivity to Concept ID and Set Name."""
        base = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs = ConceptSet(id=1, name="Set 1")
        cs.expression = ConceptSetExpression(
            items=[ConceptSetItem(concept=Concept(concept_id=123))]
        )
        base.concept_sets = [cs]
        base_hash = base.checksum()

        # Change ID
        diff_id = base.model_copy(deep=True)
        diff_id.concept_sets[0].expression.items[0].concept.concept_id = 124
        self.assertNotEqual(
            base_hash, diff_id.checksum(), "Checksum must change if Concept ID changes"
        )

        # Change Set Name (Wait, user said concept names in concept sets don't matter...
        # usually means render, but concept set name might matter if used in render?
        # Plan said: 'Changing ConceptSet.name (set name) MUST change the hash.' - adhering to plan)
        diff_name = base.model_copy(deep=True)
        diff_name.concept_sets[0].name = "Set 2"
        self.assertNotEqual(
            base_hash,
            diff_name.checksum(),
            "Checksum must change if ConceptSet Name changes",
        )

    def test_defaults_handling(self):
        """Test that default values are handled consistently."""
        # C1: Explicit False
        c1 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs1 = ConceptSet(id=1, name="Set 1")
        item1 = ConceptSetItem(
            concept=Concept(concept_id=123), isExcluded=False
        )  # Explicit default
        cs1.expression = ConceptSetExpression(items=[item1])
        c1.concept_sets = [cs1]

        # C2: Implicit Default (None or missing handled by model default)
        c2 = CohortExpression(title="Test", primary_criteria=PrimaryCriteria())
        cs2 = ConceptSet(id=1, name="Set 1")
        item2 = ConceptSetItem(
            concept=Concept(concept_id=123)
        )  # Implicit default isExcluded=False
        cs2.expression = ConceptSetExpression(items=[item2])
        c2.concept_sets = [cs2]

        # Verify defaults match logic
        self.assertEqual(item1.is_excluded, item2.is_excluded)

        self.assertEqual(
            c1.checksum(),
            c2.checksum(),
            "Checksum should be same for explicit vs implicit defaults",
        )


if __name__ == "__main__":
    unittest.main()
