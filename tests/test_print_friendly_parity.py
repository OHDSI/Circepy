import unittest
import os
import json
from circe.cohortdefinition.printfriendly.markdown_render import MarkdownRender
from circe.cohortdefinition.cohort import CohortExpression

# Helper to load resources
def get_resource_as_string(filename):
    # Depending on where pytest is run from, this path might need adjustment.
    # Assuming running from root of repo.
    path = os.path.join(os.path.dirname(__file__), 'markdown_resources', filename)
    with open(path, 'r') as f:
        return f.read()

def normalize_whitespace(text):
    """Normalize whitespace by collapsing multiple spaces/newlines into a single space and stripping."""
    if not text:
        return ""
    return " ".join(text.split())

class TestPrintFriendlyParity(unittest.TestCase):
    def setUp(self):
        self.pf = MarkdownRender()

    def assertInNormalized(self, subst, markdown, *args, **kwargs):
        norm_subst = normalize_whitespace(subst)
        norm_markdown = normalize_whitespace(markdown)
        if not args and not kwargs:
            msg = f"Normalized substring not found:\nExpected: {norm_subst}\nIn context: ...{norm_markdown[max(0, norm_markdown.find(norm_subst)-50):norm_markdown.find(norm_subst)+150]}..."
            self.assertIn(norm_subst, norm_markdown, msg)
        else:
            self.assertIn(norm_subst, norm_markdown, *args, **kwargs)

    def test_condition_era_test(self):
        json_str = get_resource_as_string("conditionEra.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. condition era of 'Concept Set 1' for the first time in the person's history, who are male &lt; 30 years old at era start and &le; 40 years old at era end; starting before January 1, 2010 and ending before December 31, 2014; era length is &gt; 15 days; containing between 1 and 5 occurrences; having no condition eras of 'Concept Set 2', starting between 90 days before and 30 days after 'Concept Set 1' start date and ending between 7 days after and 90 days after 'Concept Set 1' start date.",
            "#### 1. Inclusion Rule 1",
            "Entry events having at least 1 condition era of 'Concept Set 3' for the first time in the person's history, starting between 90 days before and 0 days before cohort entry start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_condition_occurrence_test(self):
        json_str = get_resource_as_string("conditionOccurrence.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. condition occurrence of 'Concept Set 1' (including 'Concept Set 2' source concepts) for the first time in the person's history, who are male or female, &gt;= 18 years old; starting before January 1, 2010 and ending after June 1, 2016; a condition type that is not: \"admission note\" or \"ancillary report\"; with a stop reason containing \"some stop reason\"; a provider specialty that is: \"rheumatology\"; a visit occurrence that is: \"emergency room visit\" or \"inpatient visit\"; with any of the following criteria:",
            "1. with the following event criteria: who are male &ge; 18 years old.",
            "2. having at least 1 condition occurrence of 'Concept Set 1', starting 1 days after 'Concept Set 1' start date; who are female &lt; 30 years old.",
            "#### 1. Inclusion Rule 1",
            "Entry events having at least 1 condition occurrence of 'Concept Set 3' for the first time in the person's history, starting between all days before and 1 days after cohort entry start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_death_test(self):
        json_str = get_resource_as_string("death.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. death of 'Concept Set 1' (including 'Concept Set 2' source concepts),",
            "who are female &lt; 18 years old;",
            "starting on or after January 1, 2010",
            "having no death of 'Concept Set 3', starting anytime prior to 'Concept Set 1' start date.",
            "#### 1. Inclusion Rule 1",
            "Entry events having at least 1 death of 'Concept Set 3', who are &gt; 12 years old."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_device_exposure_test(self):
        json_str = get_resource_as_string("deviceExposure.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. device exposures of 'Concept Set 1' (including 'Concept Set 2' source concepts),",
            "starting before January 1, 2010 and ending after December 31, 2010;",
            "a device type that is: \"admission note\" or \"ancillary report\";",
            "quantity &lt; 8;",
            "a provider specialty that is: \"rheumatology\" or \"rheumatology\";",
            "a visit occurrence that is: \"emergency room visit\" or \"inpatient visit\";",
            "having at least 1 device exposure of 'Concept Set 2' for the first time in the person's history, starting between all days before and 1 days after 'Concept Set 1' start date; who are female or male, between 12 and 18 years old.",
            "Restrict entry events to having at least 1 device exposure of 'Concept Set 3' for the first time in the person's history, starting anytime prior to cohort entry start date.",
            "#### 1. Inclusion Rule 1",
            "Entry events having at least 1 device exposure of 'Concept Set 3' for the first time in the person's history, starting between 30 days before and 30 days after cohort entry start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_dose_era_test(self):
        json_str = get_resource_as_string("doseEra.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. dose era of 'Concept Set 1' for the first time in the person's history,",
            "who are female or male, &gt; 18 years old at era start and &lt; 30 years old at era end;",
            "starting before January 1, 2010 and ending after January 1, 2011;",
            "unit is: \"per gram\" or \"per deciliter\";",
            "with era length &gt; 10 days;",
            "with dose value between 15 and 45;",
            "with any of the following criteria:",
            "1. having at least 1 dose era of 'Concept Set 2' for the first time in the person's history, starting between 30 days before and 0 days after 'Concept Set 1' start date.",
            "2. having at least 1 dose era of 'Concept Set 3', starting in the 30 days prior to 'Concept Set 1' start date.",
            "Restrict entry events to with all of the following criteria:",
            "1. having at least 1 dose era of 'Concept Set 2' for the first time in the person's history, starting between 60 days before and 0 days after cohort entry start date.",
            "2. having at least 1 dose era of 'Concept Set 3', starting in the 60 days prior to cohort entry start date.",
            "#### 1. Inclusion Rule 1",
            "Entry events with all of the following criteria:",
            "1. having at least 1 dose era of 'Concept Set 3' for the first time in the person's history, starting anytime on or before cohort entry start date.",
            "2. having no dose eras of 'Concept Set 2', starting anytime prior to cohort entry start date; who are &gt; 18 years old."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_drug_era_test(self):
        json_str = get_resource_as_string("drugEra.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. drug era of 'Concept Set 1' for the first time in the person's history,",
            "who are female or male, &ge; 18 years old at era start and &le; 64 years old at era end;",
            "starting before February 1, 2014 and ending after April 1, 2014;",
            "with era length &gt; 90 days;",
            "with occurrence count between 4 and 6;",
            "with all of the following criteria:",
            "1. having at least 1 drug era of 'Concept Set 2' for the first time in the person's history, starting anytime prior to 'Concept Set 1' start date.",
            "2. having at least 1 drug era of 'Concept Set 3', starting on or after January 1, 2010.",
            "#### 1. Inclusion Rule 1",
            "Entry events having at least 1 drug era of 'Concept Set 3' for the first time in the person's history, starting between 0 days before and all days after cohort entry start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_drug_exposure_test(self):
        json_str = get_resource_as_string("drugExposure.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. drug exposure of 'Concept Set 1' (including 'Concept Set 2' source concepts) for the first time in the person's history,",
            "who are female or male, &gt; 18 years old;",
            "starting after January 1, 2010 and ending before January 1, 2016;",
            "a drug type that is: \"admission note\" or \"ancillary report\";",
            "with refills = 2;",
            "with quantity &ge; 15;",
            "with days supply &lt; 30 days;",
            "with effective drug dose &lt; 15;",
            "dose unit: \"per 24 hours\";",
            "with route: \"nasal\" or \"oral\";",
            "lot number containing \"12345\";",
            "with a stop reason starting with \"some reason\";",
            "a provider specialty that is: \"general practice\" or \"urology\";",
            "a visit occurrence that is: \"emergency room visit\" or \"inpatient visit\";",
            "with all of the following criteria:",
            "1. having at least 1 drug exposure of 'Concept Set 2', starting anytime prior to 'Concept Set 1' start date.",
            "2. having at least 1 drug exposure of 'Concept Set 3', starting between 14 days before and 0 days before 'Concept Set 1' start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_measurement_test(self):
        json_str = get_resource_as_string("measurement.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. measurement of 'Concept Set 1' (including 'Concept Set 2' source concepts) for the first time in the person's history,",
            "who are female or male, &gt; 18 years old;",
            "starting on or after January 1, 2016;",
            "a measurement type that is: \"admission note\" or \"ancillary report\";",
            "with operator: \"=\" or \"&le;\";",
            "numeric value between 5 and 10;",
            "unit: \"per billion\";",
            "with value as concept: \"good\" or \"significant change\";",
            "low range &gt; 10;",
            "high range &gt; 20;",
            "low range-to-value ratio &gt; 1.2",
            "high range-to-value ratio &gt; 0.9;",
            "with an abormal result (measurement value falls outside the low and high range)",
            "a provider specialty that is: \"gastroenterology\" or \"urology\";",
            "a visit occurrence that is: \"emergency room visit\" or \"inpatient visit\";",
            "with all of the following criteria:",
            "1. having at least 1 measurement of 'Concept Set 2' for the first time in the person's history, starting anytime on or before 'Concept Set 1' start date.",
            "2. having at least 1 measurement of 'Concept Set 3', starting between 0 days before and all days after 'Concept Set 1' start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_observation_test(self):
        json_str = get_resource_as_string("observation.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. observation of 'Concept Set 1' for the first time in the person's history,",
            "who are female or male, &gt; 18 years old;",
            "starting on or after October 1, 2015;",
            "an observation type that is: \"condition procedure\" or \"discharge summary\";",
            "numeric value &lt; 30;",
            "unit: \"per hundred\";",
            "with value as concept: \"positive\" or \"good\";",
            "with value as string ending with \"obs value suffix\";",
            "with qualifier: \"total charge\";",
            "a provider specialty that is: \"health profession\" or \"psychologist\";",
            "a visit occurrence that is: \"emergency room visit\" or \"inpatient visit\";",
            "having no observation of 'Concept Set 2' for the first time in the person's history, starting anytime prior to 'Concept Set 1' start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_observation_period_test(self):
        json_str = get_resource_as_string("observationPeriod_1.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. observation period (first obsrvation period in person's history),",
            "who are &gt; 18 years old at era start and &lt; 32 years old at era end;",
            "starting before January 1, 2014 and ending after December 31, 2014;",
            "a user defiend start date of January 1, 2014 and end date of December 31, 2014;",
            "period type is: \"observation recorded from ehr\" or \"problem list from ehr\";",
            "with a length &gt; 400 days;",
            "having exactly 1 observation period, starting  1 days after observation period end date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_procedure_occurrence_test(self):
        json_str = get_resource_as_string("procedureOccurrence.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. procedure occurrence of 'Concept Set 1' (including 'Concept Set 2' source concepts) for the first time in the person's history,",
            "who are female or male, &gt; 18 years old;",
            "starting on or Before January 1, 2014;",
            "a procedure type that is: \"admission note\" or \"ancillary report\";",
            "with modifier: \"lateral meniscus structure\" or \"structure of base of lung\";",
            "with quantity &lt; 10;",
            "a provider specialty that is: \"gastroenterology\" or \"urology\";",
            "a visit occurrence that is: \"emergency room visit\" or \"inpatient visit\";",
            "having at least 1 procedure occurrence of 'Concept Set 3', starting anytime prior to 'Concept Set 1' start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_specimen_test(self):
        json_str = get_resource_as_string("specimen.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. specimen of 'Concept Set 1' for the first time in the person's history,",
            "who are female or male, &gt; 18 years old;",
            "starting before January 1, 2010;",
            "a specimen type that is: \"admission note\" or \"ancillary report\";",
            "with quantity &lt; 10;",
            "with unit: \"per 24 hours\";",
            "with anatomic site: \"lateral meniscus structure\" or \"structure of base of lung\"",
            "with disease status: \"abnormal\";",
            "with source ID starting with \"source Id Prefix\";",
            "having at least 1 specimen of 'Concept Set 2', starting anytime prior to 'Concept Set 1' start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_visit_test(self):
        json_str = get_resource_as_string("visit.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. visit occurrence of 'Concept Set 1' (including 'Concept Set 2' source concepts) for the first time in the person's history,",
            "who are female or male, between 18 and 64 years old;",
            "starting before January 1, 2010 and ending after January 7, 2010;",
            "a visit type that is: \"admission note\" or \"ancillary report\";",
            "a provider specialty that is: \"general practice\" or \"general surgery\";",
            "with length &gt; 12 days",
            "having at least 1 visit occurrence of 'Concept Set 2', starting anytime on or before 'Concept Set 1' start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_visit_detail_test(self):
        json_str = get_resource_as_string("visitDetail.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. visit detail of 'Concept Set 1' (including 'Concept Set 2' source concepts) for the first time in the person's history,",
            "who are gender in 'Concept Set 2' between 18 and 64 years old;",
            "starting before January 1, 2010 and ending after January 7, 2010;",
            "a visit detail type that is in 'Concept Set 2' concept set;",
            "a provider specialty that is in 'Concept Set 3' concept set;",
            "with length &gt; 12 days",
            "having at least 1 visit detail of 'Concept Set 3', starting anytime on or before 'Concept Set 1' start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_date_offset_test(self):
        json_str = get_resource_as_string("dateOffset.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        self.assertInNormalized("The cohort end date will be offset from index event's end date plus 7 days.", markdown)

    def test_custom_era_exit_test(self):
        json_str = get_resource_as_string("customEraExit.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "The cohort end date will be based on a continuous exposure to 'Concept Set 1':",
            "allowing 14 days between exposures, adding 1 day after exposure ends, and forcing drug exposure days supply to: 7 days."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_concept_set_simple_test(self):
        json_str = get_resource_as_string("conceptSet_simple.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_concept_set_list(expression.concept_sets)
        
        expected_substrings = [
            "### Empty Concept Set",
            "There are no concept set items in this concept set.",
            "### Only Descendants",
            "|Concept ID|Concept Name|Code|Vocabulary|Excluded|Descendants|Mapped",
            "|140168|Psoriasis|9014002|SNOMED|NO|YES|NO|",
            "### Only Excluded",
            "|140168|Psoriasis|9014002|SNOMED|YES|NO|NO|"
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_any_condition_test(self):
        json_str = get_resource_as_string("anyCondition.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        self.assertInNormalized("1. condition occurrences of any condition.", markdown)

    def test_censor_criteria_test(self):
        json_str = get_resource_as_string("censorCriteria.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "The person exits the cohort when encountering any of the following events:",
            "death of any form"
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_no_censor_criteria_test(self):
        json_str = get_resource_as_string("noCensorCriteria.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        self.assertNotIn("The person exits the cohort when encountering any of the following events:", markdown)

    def test_continuous_observation_none_test(self):
        json_str = get_resource_as_string("continuousObservation_none.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        self.assertInNormalized("People enter the cohort when observing any of the following:", markdown)

    def test_continuous_observation_prior_test(self):
        json_str = get_resource_as_string("continuousObservation_prior.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        self.assertInNormalized("People with continuous observation of 30 days before event enter the cohort when observing any of the following:", markdown)

    def test_continuous_observation_post_test(self):
        json_str = get_resource_as_string("continuousObservation_post.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        self.assertInNormalized("People with continuous observation of 30 days after event enter the cohort when observing any of the following:", markdown)

    def test_continuous_observation_prior_post_test(self):
        json_str = get_resource_as_string("continuousObservation_priorpost.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        self.assertInNormalized("People with continuous observation of 30 days before and 30 days after event enter the cohort when observing any of the following:", markdown)

    def test_count_criteria_test(self):
        json_str = get_resource_as_string("countCriteria.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. condition occurrences of 'Empty Concept Set', starting on or after January 1, 2010.",
            "2. condition occurrences of 'Empty Concept Set', who are between 18 and 64 years old; having at least 1 condition occurrence of any condition, starting between 30 days before and 30 days after 'Empty Concept Set' start date.",
            "3. condition occurrences of 'Empty Concept Set'; with all of the following criteria:",
            "1. having at least 1 condition occurrence of 'Empty Concept Set', starting anytime on or before 'Empty Concept Set' start date; who are &gt; 18 years old.",
            "2. having at least 1 condition occurrence of any condition, starting between 0 days before and all days after 'Empty Concept Set' start date; who are &lt; 64 years old.",
            "#### 1. any time",
            "Entry events having at least 1 condition occurrence of any condition.",
            "#### 2. any time +visit",
            "Entry events having at least 1 condition occurrence of 'Empty Concept Set', at same visit as cohort entry.",
            "#### 3. any time +visit +op",
            "Entry events having at least 1 condition occurrence of any condition, at same visit as cohort entry and allow events outside observation period.",
            "#### 4. prior time",
            "Entry events having at least 1 condition occurrence of any condition, starting anytime on or before cohort entry start date.",
            "#### 5. prior time +visit",
            "Entry events having at least 1 condition occurrence of 'Empty Concept Set', starting anytime on or before cohort entry start date; at same visit as cohort entry.",
            "#### 6. prior time +visit +op",
            "Entry events having at least 1 condition occurrence of any condition, starting anytime on or before cohort entry start date; at same visit as cohort entry and allow events outside observation period.",
            "#### 7. sub-groups",
            "Entry events with all of the following criteria:",
            "1. having at least 1 condition occurrence of 'Empty Concept Set', starting anytime on or before cohort entry start date.",
            "2. having no condition occurrences of 'Empty Concept Set', starting between 0 days before and all days after cohort entry start date.",
            "3. with any of the following criteria:",
            "1. having at least 1 condition occurrence of 'Empty Concept Set', starting between 30 days before and 30 days after cohort entry start date.",
            "2. having no condition occurrences of 'Empty Concept Set', starting anytime up to 31 days before cohort entry start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_count_distinct_criteria_test(self):
        json_str = get_resource_as_string("countDistinctCriteria.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. condition occurrences of 'Empty Concept Set', starting on or after January 1, 2010.",
            "2. condition occurrences of 'Empty Concept Set', who are between 18 and 64 years old; having at least 1 distinct standard concepts from condition occurrence of any condition, starting between 30 days before and 30 days after 'Empty Concept Set' start date.",
            "3. condition occurrences of 'Empty Concept Set'; with all of the following criteria:",
            "1. having at least 1 distinct standard concepts from condition occurrence of 'Empty Concept Set', starting anytime on or before 'Empty Concept Set' start date; who are &gt; 18 years old.",
            "2. having at least 1 distinct start dates from condition occurrence of 'Empty Concept Set', starting anytime on or before 'Empty Concept Set' start date; who are &gt; 18 years old.",
            "3. having at least 1 distinct visits from condition occurrence of any condition, starting between 0 days before and all days after 'Empty Concept Set' start date; who are &lt; 64 years old."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_date_adjust_test(self):
        json_str = get_resource_as_string("dateAdjust.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        expected_substrings = [
            "1. condition eras of 'Concept Set 1', starting 10 days after and ending 20 days after the event start date.",
            "2. condition occurrences of 'Concept Set 1', starting 30 days after and ending 40 days after the event end date.",
            "3. dose eras of 'Concept Set 1', starting 10 days after and ending 20 days after the event start date.",
            "4. drug eras of 'Concept Set 1', starting 10 days after and ending 20 days after the event start date.",
            "6. device exposures of 'Concept Set 1', starting on the event start date and ending 20 days after the event end date.",
            "7. measurements of 'Concept Set 1', starting on and ending 20 days after the event end date.",
            "8. observations of 'Concept Set 1', starting 10 days after and ending 20 days after the event start date.",
            "9. observation periods, starting 10 days after and ending 20 days after the event start date.",
            "10. procedure occurrences of 'Concept Set 1', starting 10 days after and ending 20 days after the event start date.",
            "11. specimens of 'Concept Set 1', starting 10 days after and ending 20 days after the event start date.",
            "12. visit occurrences of 'Concept Set 1', starting 10 days after and ending 20 days after the event start date.",
            "13. visit details of 'Concept Set 1', starting 10 days after and ending 20 days after the event start date."
        ]
        for subst in expected_substrings:
            self.assertInNormalized(subst, markdown)

    def test_empty_concept_list_test(self):
        json_str = get_resource_as_string("emptyConceptList.json")
        expression = CohortExpression.model_validate_json(json_str)
        markdown = self.pf.render_cohort_expression(expression)
        
        self.assertInNormalized("1. condition occurrences of 'Concept Set 1', a provider specialty that is: [none specified]; a visit occurrence that is: [none specified].", markdown)

if __name__ == '__main__':
    unittest.main()
