"""
Complex Cohort Definition Example

This example demonstrates advanced features including:
- Multiple criteria with time windows
- Correlated criteria (additional criteria)
- Inclusion rules
- Age and gender restrictions
"""

from circe import CohortExpression
from circe.api import build_cohort_query
from circe.cohortdefinition import (
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    DrugExposure,
    InclusionRule,
    Measurement,
    Occurrence,
    PrimaryCriteria,
)
from circe.cohortdefinition.cohort_expression_query_builder import (
    BuildExpressionQueryOptions,
)
from circe.cohortdefinition.core import (
    NumericRange,
    ObservationFilter,
    ResultLimit,
    Window,
    WindowBound,
)
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def create_complex_cohort():
    """
    Create a cohort for patients with:
    1. Type 2 Diabetes diagnosis
    2. Metformin prescription within 30 days after diagnosis
    3. Age 18+ at index
    4. No insulin exposure in the 180 days before diagnosis
    5. Inclusion rule: HbA1c measurement within 6 months after diagnosis
    6. Censoring: Observation ends if patient develops ESRD or enters hospice
    """

    # Concept Set 1: Type 2 Diabetes
    diabetes_concepts = ConceptSet(
        id=1,
        name="Type 2 Diabetes Mellitus",
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(concept_id=201826, concept_name="Type 2 diabetes mellitus"),
                    include_descendants=True,
                )
            ]
        ),
    )

    # Concept Set 2: Metformin
    metformin_concepts = ConceptSet(
        id=2,
        name="Metformin",
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(concept_id=1503297, concept_name="Metformin"),
                    include_descendants=True,
                )
            ]
        ),
    )

    # Concept Set 3: Insulin (for exclusion)
    insulin_concepts = ConceptSet(
        id=3,
        name="Insulin",
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(concept_id=1511348, concept_name="Insulin"),
                    include_descendants=True,
                )
            ]
        ),
    )

    # Concept Set 4: HbA1c measurement
    hba1c_concepts = ConceptSet(
        id=4,
        name="Hemoglobin A1c measurement",
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(
                        concept_id=3004410,
                        concept_name="Hemoglobin A1c/Hemoglobin.total in Blood",
                    ),
                    include_descendants=True,
                )
            ]
        ),
    )

    # Concept Set 5: End-Stage Renal Disease (censoring event)
    esrd_concepts = ConceptSet(
        id=5,
        name="End-Stage Renal Disease",
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(concept_id=46271022, concept_name="End stage renal disease"),
                    include_descendants=True,
                )
            ]
        ),
    )

    # Concept Set 6: Hospice Care (censoring event)
    hospice_concepts = ConceptSet(
        id=6,
        name="Hospice Care",
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(concept_id=8536, concept_name="Hospice care"),
                    include_descendants=True,
                )
            ]
        ),
    )

    # Primary Criteria: First Type 2 Diabetes diagnosis
    primary_criteria = PrimaryCriteria(
        criteria_list=[
            ConditionOccurrence(
                codeset_id=1,
                first=True,
                condition_type_exclude=False,
                # Age restriction at the time of diagnosis
                age=NumericRange(value=18, op="gte"),
            )
        ],
        observation_window=ObservationFilter(prior_days=0, post_days=0),
        primary_limit=ResultLimit(type="All"),
    )

    # Additional Criteria: Metformin within 30 days after diagnosis
    metformin_criteria = CorelatedCriteria(
        criteria=DrugExposure(codeset_id=2, first=False, drug_type_exclude=False),
        start_window=Window(
            use_event_end=False,
            start=WindowBound(coeff=-1, days=0),  # Index date
            end=WindowBound(coeff=1, days=30),  # 30 days after
        ),
        occurrence=Occurrence(
            type=2,  # At least
            count=1,
            is_distinct=False,
        ),
    )

    # Additional Criteria: NO insulin in 180 days before diagnosis
    insulin_exclusion = CorelatedCriteria(
        criteria=DrugExposure(codeset_id=3, first=False, drug_type_exclude=False),
        start_window=Window(
            use_event_end=False,
            start=WindowBound(coeff=-1, days=180),  # 180 days before
            end=WindowBound(coeff=-1, days=1),  # Day before index
        ),
        occurrence=Occurrence(
            type=0,  # Exactly
            count=0,  # Zero occurrences (exclusion)
            is_distinct=False,
        ),
    )

    # Combine additional criteria
    additional_criteria = CriteriaGroup(
        type="ALL",  # Must meet all criteria
        criteria_list=[metformin_criteria, insulin_exclusion],
        demographic_criteria_list=None,
        groups=None,
    )

    # Inclusion Rule 1: HbA1c measurement within 6 months after diagnosis
    hba1c_measurement = CorelatedCriteria(
        criteria=Measurement(codeset_id=4, first=False, measurement_type_exclude=False),
        start_window=Window(
            use_event_end=False,
            start=WindowBound(coeff=-1, days=0),  # Index date
            end=WindowBound(coeff=1, days=180),  # 6 months (180 days) after
        ),
        occurrence=Occurrence(
            type=2,  # At least
            count=1,  # One measurement
            is_distinct=False,
        ),
    )

    inclusion_rule_hba1c = InclusionRule(
        name="Has HbA1c measurement within 6 months",
        description="Patient must have at least one HbA1c measurement within 6 months after diagnosis",
        expression=CriteriaGroup(
            type="ALL",
            criteria_list=[hba1c_measurement],
            demographic_criteria_list=None,
            groups=None,
        ),
    )

    # Inclusion Rule 2: Follow-up visit within 90 days
    followup_visit = CorelatedCriteria(
        criteria=ConditionOccurrence(
            codeset_id=1,  # Type 2 Diabetes
            first=False,
            condition_type_exclude=False,
        ),
        start_window=Window(
            use_event_end=False,
            start=WindowBound(coeff=1, days=1),  # Day after index
            end=WindowBound(coeff=1, days=90),  # 90 days after
        ),
        occurrence=Occurrence(
            type=2,  # At least
            count=1,  # One follow-up
            is_distinct=False,
        ),
    )

    inclusion_rule_followup = InclusionRule(
        name="Has follow-up visit within 90 days",
        description="Patient must have at least one follow-up visit for diabetes within 90 days after initial diagnosis",
        expression=CriteriaGroup(
            type="ALL",
            criteria_list=[followup_visit],
            demographic_criteria_list=None,
            groups=None,
        ),
    )

    # Censoring Criteria: Events that end observation for the patient
    # These represent serious complications or end-of-life care that would alter treatment
    censoring_criteria = [
        # ESRD diagnosis - a serious complication requiring different treatment approach
        ConditionOccurrence(codeset_id=5, first=False, condition_type_exclude=False),
        # Hospice care - indicates end-of-life care, patient no longer appropriate for study
        ConditionOccurrence(codeset_id=6, first=False, condition_type_exclude=False),
    ]

    # Create the complete cohort expression
    cohort = CohortExpression(
        title="New Type 2 Diabetes Patients Started on Metformin with Monitoring",
        concept_sets=[
            diabetes_concepts,
            metformin_concepts,
            insulin_concepts,
            hba1c_concepts,
            esrd_concepts,
            hospice_concepts,
        ],
        primary_criteria=primary_criteria,
        additional_criteria=additional_criteria,
        inclusion_rules=[inclusion_rule_hba1c, inclusion_rule_followup],
        censoring_criteria=censoring_criteria,
        qualified_limit=ResultLimit(type="First"),  # First qualifying event per person
        expression_limit=ResultLimit(type="All"),
    )

    return cohort


if __name__ == "__main__":
    # Create the complex cohort
    print("Creating complex Type 2 Diabetes cohort with multiple criteria...")
    cohort = create_complex_cohort()

    # Display cohort information
    print(f"\nCohort Title: {cohort.title}")
    print(f"Number of Concept Sets: {len(cohort.concept_sets)}")
    print("Concept Sets:")
    for cs in cohort.concept_sets:
        print(f"  - {cs.name}")

    print(f"\nAdditional Criteria: {len(cohort.additional_criteria.criteria_list)} conditions")
    print(f"Inclusion Rules: {len(cohort.inclusion_rules)} rules")
    for rule in cohort.inclusion_rules:
        print(f"  - {rule.name}")
    print(f"Censoring Criteria: {len(cohort.censoring_criteria)} events")
    for _i, criteria in enumerate(cohort.censoring_criteria, 1):
        # Get the criteria type from the wrapped object
        criteria_dict = criteria.model_dump(by_alias=True)
        criteria_type = list(criteria_dict.keys())[0]
        print(f"  - {criteria_type}")

    # Generate SQL
    print("\nGenerating SQL...")
    # Note: For SqlRender compatibility, leave schema parameters unset
    # to preserve @vocabulary_database_schema notation in the output.
    # SqlRender will replace these at runtime with actual schema names.
    options = BuildExpressionQueryOptions()
    options.cohort_id = 2
    options.generate_stats = True

    sql = build_cohort_query(cohort, options)

    # Save outputs
    sql_file = "complex_diabetes_cohort.sql"
    with open(sql_file, "w") as f:
        f.write(sql)
    print(f"SQL saved to: {sql_file}")

    json_file = "complex_diabetes_cohort.json"
    with open(json_file, "w") as f:
        # Note: For ATLAS compatibility, concepts should have complete metadata (see ATLAS_COMPATIBILITY.md)
        f.write(cohort.model_dump_json(indent=2, by_alias=True, exclude_none=True))
    print(f"Cohort definition saved to: {json_file} (Java/ATLAS-compatible format)")

    print("\nCohort summary:")
    print("  - Index: First Type 2 Diabetes diagnosis")
    print("  - Age: 18+ at diagnosis")
    print("  - Must have: Metformin within 30 days after diagnosis")
    print("  - Must not have: Insulin in 180 days before diagnosis")
    print("  - Inclusion 1: HbA1c measurement within 6 months after diagnosis")
    print("  - Inclusion 2: Follow-up visit within 90 days after diagnosis")
    print("  - Censoring: Observation ends if ESRD or hospice care occurs")
