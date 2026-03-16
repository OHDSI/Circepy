import unittest

from circe.cohortdefinition.printfriendly.markdown_render import MarkdownRender
from circe.vocabulary.concept import ConceptSet


class TestMarkdownRenderCoverage(unittest.TestCase):
    """
    Tests specifically targeting edge cases and error handling in MarkdownRender
    to improve code coverage.
    """

    def setUp(self):
        self.renderer = MarkdownRender()

    def test_render_cohort_expression_string_input(self):
        # Line 83: string input
        cohort_json = '{"title": "Test String Input", "primaryCriteria": {"observationWindow": {"priorDays": 0, "postDays": 0}, "primaryEvents": []}}'
        output = self.renderer.render_cohort_expression(cohort_json)
        # Title is not rendered in the template, so check for structure
        self.assertIn("Cohort Entry Events", output)
        self.assertIn("Cohort Exit", output)

    def test_render_cohort_expression_with_concept_sets(self):
        # Line 90: cohort expression has concept sets
        cohort_json = '{"title": "With CS", "conceptSets": [{"id": 1, "name": "CS1", "expression": {"items": []}}], "primaryCriteria": {"observationWindow": {"priorDays": 0, "postDays": 0}, "primaryEvents": []}}'
        output = self.renderer.render_cohort_expression(cohort_json, include_concept_sets=True)
        self.assertIn("Concept Sets", output)
        self.assertIn("CS1", output)

    def test_render_cohort_expression_empty_input(self):
        # Line 86: empty input
        output = self.renderer.render_cohort_expression(None)
        self.assertIn("Invalid Cohort Expression", output)
        self.assertIn("No cohort expression provided", output)

    def test_render_concept_set_list_string_input_list(self):
        # Lines 117-120: string input as list
        cs_list_json = '[{"id": 1, "name": "CS1", "expression": {"items": []}}]'
        output = self.renderer.render_concept_set_list(cs_list_json)
        self.assertIn("CS1", output)

    def test_render_concept_set_list_string_input_single(self):
        # Lines 121-122: string input as single object (edge case for loose JSON)
        cs_json = '{"id": 2, "name": "CS2", "expression": {"items": []}}'
        output = self.renderer.render_concept_set_list(cs_json)
        self.assertIn("CS2", output)

    def test_render_concept_set_list_empty(self):
        # Line 125: empty concept sets
        output = self.renderer.render_concept_set_list([])
        self.assertIn("No concept sets specified", output)
        
        output_none = self.renderer.render_concept_set_list(None)
        self.assertIn("No concept sets specified", output_none)

    def test_render_concept_set_string_input(self):
        # Lines 147-151: string input for single concept set
        cs_json = '{"id": 3, "name": "CS3", "expression": {"items": []}}'
        output = self.renderer.render_concept_set(cs_json)
        self.assertIn("CS3", output)

    def test_codeset_name_not_found(self):
        # Line 177: ID not found in concept sets
        # Setup renderer with some concept sets
        cs = ConceptSet(id=1, name="Existing CodeSet", expression={"items": []})
        renderer = MarkdownRender(concept_sets=[cs])
        
        # Test ID that doesn't exist
        name = renderer._codeset_name(999, default_name="Default")
        self.assertEqual(name, "Default")
        
        # Line 175: ID found
        name_found = renderer._codeset_name(1, default_name="Default")
        self.assertEqual(name_found, "'Existing CodeSet'")
        
        # Line 170: ID is None
        name_none = renderer._codeset_name(None, default_name="Default")
        self.assertEqual(name_none, "Default")

    def test_format_date_invalid(self):
        # Lines 195-197: Invalid date handling
        # Case 1: Wrong formatting but length 10 string -> triggers ValueError inside strptime -> returns "_invalid date_"
        self.assertEqual(self.renderer._format_date("2020/01/01"), "_invalid date_") 
        
        # Case 2: String that is not length 10 -> returns input as is
        self.assertEqual(self.renderer._format_date("2020/01"), "2020/01")
        
        # Case 3: Non-string -> returns input as is (line 195)
        self.assertEqual(self.renderer._format_date(12345), 12345)

    def test_format_date_valid(self):
        # Lines 193-194: Valid date
        # "2020-01-05" -> "January 5, 2020"
        self.assertEqual(self.renderer._format_date("2020-01-05"), "January 5, 2020")
        # Check lstrip("0") behavior
        self.assertEqual(self.renderer._format_date("2020-12-10"), "December 10, 2020")

    def test_format_number_edge_cases(self):
        # Line 209: None input
        self.assertEqual(self.renderer._format_number(None), "")
        
        # Line 213: Float that is integer
        self.assertEqual(self.renderer._format_number(1000.0), "1,000")
        
        # Normal float
        self.assertEqual(self.renderer._format_number(1000.5), "1,000.5")

if __name__ == '__main__':
    unittest.main()
