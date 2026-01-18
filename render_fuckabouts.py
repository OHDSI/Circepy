import os
from circe.cohortdefinition import CohortExpression
from circe.api import MarkdownRender


def get_resource_as_string(filename):
    # Depending on where pytest is run from, this path might need adjustment.
    # Assuming running from root of repo.
    path = os.path.join('tests', 'markdown_resources', filename)
    with open(path, 'r') as f:
        return f.read()


pf = MarkdownRender()
json = get_resource_as_string("conditionOccurrence.json")

expected_substrings = [
    "1. condition occurrence of 'Concept Set 1' (including 'Concept Set 2' source concepts)",
    "for the first time in the person's history, who are male or female, &gt;= 18 years old; starting before January 1, 2010 and ending after June 1, 2016; a condition type that is not: \"admission note\" or \"ancillary report\"; with a stop reason containing \"some stop reason\"; a provider specialty that is: \"rheumatology\"; a visit occurrence that is: \"emergency room visit\" or \"inpatient visit\"; with any of the following criteria:",
    "1. with the following event criteria: who are male &ge; 18 years old.",
    "2. having at least 1 condition occurrence of 'Concept Set 1', starting  1 days after 'Concept Set 1' start date; who are female &lt; 30 years old.",
    "#### 1. Inclusion Rule 1",
    "Entry events having at least 1 condition occurrence of 'Concept Set 3' for the first time in the person's history, starting between all days before and 1 days after cohort entry start date."
]
print(pf.render_cohort_expression(json))

for x in expected_substrings:
    print(x in pf.render_cohort_expression(json))
