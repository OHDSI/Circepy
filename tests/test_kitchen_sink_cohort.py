import unittest

from circe.cohortdefinition.cohort import CohortExpression
from circe.cohortdefinition.core import (
    CollapseSettings,
    CollapseType,
    CustomEraStrategy,
    DateRange,
    NumericRange,
    ObservationFilter,
    Period,
    ResultLimit,
    TextFilter,
    Window,
    WindowBound,
)
from circe.cohortdefinition.criteria import (
    ConditionEra,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    Death,
    DemographicCriteria,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
    InclusionRule,
    Measurement,
    Observation,
    ObservationPeriod,
    Occurrence,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
    VisitOccurrence,
)
from circe.vocabulary.concept import (
    Concept,
    ConceptSet,
    ConceptSetExpression,
    ConceptSetItem,
)


class TestKitchenSinkCohort(unittest.TestCase):
    """Test comprehensive 'Kitchen Sink' cohort definition."""

    def create_kitchen_sink_cohort(self) -> CohortExpression:
        """Creates a cohort definition using ALL classes and options."""

        # 1. Concept Sets
        concept_sets = [
            ConceptSet(
                id=1,
                name="T2DM",
                expression=ConceptSetExpression(
                    items=[
                        ConceptSetItem(
                            concept=Concept(
                                concept_id=201826,
                                concept_name="Type 2 diabetes mellitus",
                                standard_concept="S",
                                invalid_reason="V",
                                concept_code="201826",
                                domain_id="Condition",
                                vocabulary_id="SNOMED",
                                concept_class_id="Clinical Finding",
                            ),
                            is_excluded=False,
                            include_descendants=True,
                            include_mapped=False,
                        )
                    ]
                ),
            ),
            ConceptSet(
                id=2,
                name="Metformin",
                expression=ConceptSetExpression(
                    items=[
                        ConceptSetItem(
                            concept=Concept(
                                concept_id=1112807, concept_name="Metformin"
                            ),
                            is_excluded=False,
                            include_descendants=True,
                            include_mapped=True,
                        )
                    ]
                ),
            ),
        ]

        # 2. Criteria Definitions (using non-default values where possible)

        # Condition Occurrence
        condition_occurrence = ConditionOccurrence(
            codeset_id=1,
            first=True,
            occurrence_start_date=DateRange(value="2010-01-01", op="gt"),
            occurrence_end_date=DateRange(value="2020-01-01", op="lt"),
            condition_type=[
                Concept(concept_id=32020, concept_name="EHR encounter diagnosis")
            ],
            condition_type_exclude=True,
            stop_reason=TextFilter(text="recovered", op="contains"),
            condition_source_concept=123,
            age=NumericRange(value=18, op="gt"),
            gender=[Concept(concept_id=8507, concept_name="Male")],
            provider_specialty=[
                Concept(concept_id=38004456, concept_name="Endocrinology")
            ],
            visit_type=[Concept(concept_id=9201, concept_name="Inpatient Visit")],
            condition_status=[
                Concept(concept_id=4230359, concept_name="Final diagnosis")
            ],
        )

        # Drug Exposure
        drug_exposure = DrugExposure(
            codeset_id=2,
            first=False,
            occurrence_start_date=DateRange(value="2010-01-01", op="gt"),
            occurrence_end_date=DateRange(value="2020-01-01", op="lt"),
            drug_type=[
                Concept(concept_id=38000177, concept_name="Prescription written")
            ],
            drug_type_exclude=False,
            stop_reason=TextFilter(text="adversereaction", op="endswith"),
            refills=NumericRange(value=1, op="gte"),
            quantity=NumericRange(value=30, op="lte"),
            days_supply=NumericRange(value=30, op="get"),
            route_concept=[Concept(concept_id=4132161, concept_name="Oral")],
            effective_drug_source_concept=999,
            dose_unit=[Concept(concept_id=8576, concept_name="milligram")],
            lot_number=TextFilter(text="LOT123", op="eq"),
            age=NumericRange(value=50, op="lt"),
            gender=[Concept(concept_id=8532, concept_name="Female")],
            provider_specialty=[
                Concept(concept_id=38004456, concept_name="Endocrinology")
            ],
            visit_type=[Concept(concept_id=9202, concept_name="Outpatient Visit")],
        )

        # Procedure Occurrence
        procedure = ProcedureOccurrence(
            codeset_id=1,
            first=True,
            occurrence_start_date=DateRange(value="2015-01-01", op="gt"),
            procedure_type=[
                Concept(concept_id=38000275, concept_name="EHR order list entry")
            ],
            procedure_type_exclude=True,
            modifier=[Concept(concept_id=123, concept_name="Modifier")],
            quantity=NumericRange(value=1, op="eq"),
            procedure_source_concept=456,
            age=NumericRange(value=20, op="gt"),
        )

        # Visit Occurrence
        visit = VisitOccurrence(
            codeset_id=0,  # No codeset
            first=True,
            occurrence_start_date=DateRange(value="2010-01-01", op="gt"),
            occurrence_end_date=DateRange(value="2020-01-01", op="lt"),
            visit_type=[
                Concept(concept_id=44818518, concept_name="Visit derived from EHR")
            ],
            visit_type_exclude=False,
            visit_source_concept=789,
            visit_length=NumericRange(value=1, op="gt"),
            age=NumericRange(value=18, op="gt"),
            gender=[Concept(concept_id=8507, concept_name="Male")],
            provider_specialty=[
                Concept(concept_id=38003845, concept_name="General Practice")
            ],
            place_of_service=[
                Concept(concept_id=8717, concept_name="Inpatient Hospital")
            ],
            place_of_service_location=12345,
        )

        # Measurement
        measurement = Measurement(
            codeset_id=1,
            first=True,
            occurrence_start_date=DateRange(value="2010-01-01", op="gt"),
            measurement_type=[Concept(concept_id=44818702, concept_name="Lab result")],
            measurement_type_exclude=True,
            operator=[Concept(concept_id=4172703, concept_name=">")],
            value_as_number=NumericRange(value=5.7, op="gt"),
            value_as_concept=[Concept(concept_id=45878245, concept_name="High")],
            unit=[Concept(concept_id=8840, concept_name="mg/dL")],
            range_low=NumericRange(value=0, op="gt"),
            range_high=NumericRange(value=100, op="lt"),
            range_low_ratio=NumericRange(value=0.5, op="gt"),
            range_high_ratio=NumericRange(value=1.5, op="lt"),
            abnormal=True,
            measurement_source_concept=111,
            age=NumericRange(value=30, op="gt"),
        )

        # Observation
        observation = Observation(
            codeset_id=1,
            first=False,
            occurrence_start_date=DateRange(value="2010-01-01", op="gt"),
            observation_type=[
                Concept(
                    concept_id=38000280, concept_name="Observation recorded from EHR"
                )
            ],
            observation_type_exclude=False,
            value_as_number=NumericRange(value=10, op="gt"),
            value_as_string=TextFilter(text="positive", op="eq"),
            value_as_concept=[Concept(concept_id=45877994, concept_name="Severe")],
            qualifier=[Concept(concept_id=45882570, concept_name="Left")],
            unit=[Concept(concept_id=8510, concept_name="unit")],
            observation_source_concept=222,
            age=NumericRange(value=40, op="gt"),
        )

        # Device Exposure
        device = DeviceExposure(
            codeset_id=1,
            first=True,
            occurrence_start_date=DateRange(value="2010-01-01", op="gt"),
            device_type=[Concept(concept_id=44818707, concept_name="Device inferred")],
            device_type_exclude=True,
            unique_device_id=TextFilter(text="UDI123", op="eq"),
            quantity=NumericRange(value=1, op="eq"),
            device_source_concept=333,
            age=NumericRange(value=50, op="gt"),
        )

        # Specimen
        specimen = Specimen(
            codeset_id=1,
            first=True,
            occurrence_start_date=DateRange(value="2010-01-01", op="gt"),
            specimen_type=[
                Concept(concept_id=38000281, concept_name="Specimen from EHR")
            ],
            specimen_type_exclude=True,
            unit=[Concept(concept_id=8576, concept_name="milligram")],
            anatomic_site=[Concept(concept_id=4044352, concept_name="Arm")],
            disease_status=[Concept(concept_id=4066212, concept_name="Healthy")],
            specimen_source_concept=555,
        )

        emographic = DemographicCriteria(
            age=NumericRange(value=18, op="gt"),
            gender=[Concept(concept_id=8507, concept_name="Male")],
            race=[Concept(concept_id=8527, concept_name="White")],
            ethnicity=[
                Concept(concept_id=38003564, concept_name="Not Hispanic or Latino")
            ],
            occurrence_start_date=DateRange(value="2010-01-01", op="gt"),
            occurrence_end_date=DateRange(value="2020-01-01", op="lt"),
        )

        # Groups with nested criteria
        group1 = CriteriaGroup(
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(codeset_id=1),
                    occurrence=Occurrence(type=2, count=1),
                ),
                CorelatedCriteria(
                    criteria=DrugExposure(codeset_id=2, first=True),
                    occurrence=Occurrence(type=2, count=1),
                ),
            ],
            demographic_criteria_list=[emographic],
            groups=[],
        )

        # 3. Primary Criteria
        getattr(
            # Need to construct PrimaryCriteria manually or via helper
            # But wait, PrimaryCriteria uses CriteriaList, not nested Criteria objects directly
            # The structure in core.py for PrimaryCriteria is:
            # criteria_list: List[Criteria]
            # observation_window: ObservationFilter
            # primary_limit: ResultLimit
            None,
            "none",
            None,
        )

        # Re-import PrimaryCriteria properly
        from circe.cohortdefinition.criteria import PrimaryCriteria

        # Complex Primary Criteria
        # Note: We need to use "Criteria" objects here, which wrap the domain criteria
        # and add window/adjustment info.

        # Wrapped Criteria 1: Condition with Window
        crit1 = ConditionOccurrence(codeset_id=1, age=NumericRange(value=18, op="gt"))

        # Construction of Primary Criteria
        primary = PrimaryCriteria(
            criteria_list=[crit1],
            observation_window=ObservationFilter(prior_days=365, post_days=0),
            primary_limit=ResultLimit(type="First"),
        )

        # 4. Inclusion Rules

        # Rule 1: Must have Metformin
        rule1_crit = DrugExposure(
            codeset_id=2, first=True, age=NumericRange(value=18, op="gt")
        )

        # Corelated Criteria (Windowed)
        # We need to wrap the drug exposure in a CorelatedCriteria/WindowedCriteria structure usually
        # But InclusionRule takes a CriteriaGroup

        # Let's create a CorelatedCriteria wrapper for the drug exposure
        # The internal structure is a bit complex.
        # CriteriaGroup -> criteria_list (which are CorelatedCriteria)

        corelated_crit = CorelatedCriteria(
            criteria=rule1_crit,
            start_window=Window(
                start=WindowBound(coeff=-1, days=30),
                end=WindowBound(coeff=1, days=30),
                use_index_end=False,
                use_event_end=False,
            ),
            occurrence=Occurrence(
                type=2,  # AT_LEAST
                count=1,
            ),
        )

        rule1_group = CriteriaGroup(
            type="ALL",
            criteria_list=[corelated_crit],
            demographic_criteria_list=[],
            groups=[group1],  # Nest group1 here to use it
            count=1,  # Match at least 1
        )

        rule1 = InclusionRule(
            name="Metformin User",
            description="Patient must be on Metformin",
            expression=rule1_group,
        )

        # 4b. Additional Criteria Types (New)

        # Visit Detail
        visit_detail = VisitDetail(
            codeset_id=1,
            first=True,
            visit_detail_start_date=DateRange(value="2010-01-01", op="gt"),
            visit_detail_end_date=DateRange(value="2020-01-01", op="lt"),
            visit_detail_type_exclude=False,
            visit_detail_source_concept=123,
            visit_detail_length=NumericRange(value=1, op="gt"),
            age=NumericRange(value=18, op="gt"),
            place_of_service_location=999,
        )

        # Observation Period
        obs_period = ObservationPeriod(
            first=True,
            period_start_date=DateRange(value="2010-01-01", op="gt"),
            period_end_date=DateRange(value="2020-01-01", op="lt"),
            period_type=[
                Concept(
                    concept_id=38000280, concept_name="Observation recorded from EHR"
                )
            ],
            period_length=NumericRange(value=365, op="gt"),
            age_at_start=NumericRange(value=18, op="gt"),
            age_at_end=NumericRange(value=90, op="lt"),
            user_defined_period=Period(start_date="2010-01-01", end_date="2020-12-31"),
        )

        # Payer Plan Period
        payer_plan = PayerPlanPeriod(
            first=True,
            period_start_date=DateRange(value="2010-01-01", op="gt"),
            period_end_date=DateRange(value="2020-01-01", op="lt"),
            period_length=NumericRange(value=30, op="gt"),
            age_at_start=NumericRange(value=18, op="gt"),
            age_at_end=NumericRange(value=65, op="lt"),
            gender=[Concept(concept_id=8507, concept_name="Male")],
            payer_concept=1,
            plan_concept=2,
            sponsor_concept=3,
            stop_reason_concept=4,
            payer_source_concept=100,
            plan_source_concept=200,
            sponsor_source_concept=300,
            stop_reason_source_concept=400,
            user_defined_period=Period(start_date="2010-01-01", end_date="2015-01-01"),
        )

        # Condition Era
        condition_era = ConditionEra(
            codeset_id=1,
            first=True,
            era_start_date=DateRange(value="2010-01-01", op="gt"),
            era_end_date=DateRange(value="2020-01-01", op="lt"),
            occurrence_count=NumericRange(value=1, op="gt"),
            era_length=NumericRange(value=30, op="gt"),
            age_at_start=NumericRange(value=18, op="gt"),
            age_at_end=NumericRange(value=90, op="lt"),
            gender=[Concept(concept_id=8532, concept_name="Female")],
        )

        # Drug Era
        drug_era = DrugEra(
            codeset_id=2,
            first=True,
            era_start_date=DateRange(value="2010-01-01", op="gt"),
            era_end_date=DateRange(value="2020-01-01", op="lt"),
            occurrence_count=NumericRange(value=1, op="gt"),
            gap_days=NumericRange(value=30, op="lt"),
            era_length=NumericRange(value=30, op="gt"),
            age_at_start=NumericRange(value=18, op="gt"),
            age_at_end=NumericRange(value=90, op="lt"),
            gender=[Concept(concept_id=8507, concept_name="Male")],
        )

        # Dose Era
        dose_era = DoseEra(
            codeset_id=2,
            first=True,
            era_start_date=DateRange(value="2010-01-01", op="gt"),
            era_end_date=DateRange(value="2020-01-01", op="lt"),
            unit=[Concept(concept_id=8576, concept_name="milligram")],
            dose_value=NumericRange(value=500, op="gt"),
            era_length=NumericRange(value=30, op="gt"),
            age_at_start=NumericRange(value=18, op="gt"),
            age_at_end=NumericRange(value=90, op="lt"),
            gender=[Concept(concept_id=8507, concept_name="Male")],
        )

        # 5. Censoring Criteria
        # Add new criteria to censoring list to verify they serialize correctly
        censoring = [
            Death(first=True),
            visit_detail,
            obs_period,
            payer_plan,
            condition_era,
            drug_era,
            dose_era,
            # Add previously unused criteria
            condition_occurrence,
            drug_exposure,
            procedure,
            visit,
            measurement,
            observation,
            device,
            specimen,
        ]

        # 6. Cohort Expression
        cohort = CohortExpression(
            title="Kitchen Sink Cohort",
            description="A comprehensive cohort definition testing all features.",
            concept_sets=concept_sets,
            primary_criteria=primary,
            inclusion_rules=[rule1],
            censoring_criteria=censoring,
            collapse_settings=CollapseSettings(
                era_pad=0, collapse_type=CollapseType.ERA
            ),
            censor_window=Period(start_date="2010-01-01", end_date="2025-01-01"),
            # End Strategies - Using CustomEraStrategy this time
            end_strategy=CustomEraStrategy(
                drug_codeset_id=2, gap_days=30, offset=7, days_supply_override=0
            ),
        )

        return cohort

    def test_kitchen_sink_serialization(self):
        """Test that the kitchen sink cohort can be serialized and deserialized."""
        cohort = self.create_kitchen_sink_cohort()

        # Serialize
        json_str = cohort.model_dump_json(indent=2)

        # Basic validation
        self.assertIn("Kitchen Sink Cohort", json_str)
        self.assertIn("Type 2 diabetes mellitus", json_str)
        self.assertIn("Metformin", json_str)
        self.assertIn("CustomEra", json_str)

        # Deserialize
        cohort_restored = CohortExpression.model_validate_json(json_str)

        # Check parity
        self.assertEqual(cohort.title, cohort_restored.title)
        self.assertEqual(len(cohort.concept_sets), 2)
        self.assertEqual(len(cohort.inclusion_rules), 1)
        self.assertIsInstance(cohort.end_strategy, CustomEraStrategy)
        self.assertEqual(cohort.end_strategy.offset, 7)


if __name__ == "__main__":
    unittest.main()
